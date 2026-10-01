"""Causal order-flow features at every lab signal (data up to the END of the signal minute). Directional ones signed by trade dir."""
import sys; sys.path.insert(0, "../bt"); sys.path.insert(0, "../lab")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import gcdata as G_, lab
m1 = G_.load_1m(); idx = m1.index
OF = pd.read_parquet("of_1m.parquet").reindex(idx).fillna(0.0)       # align to the 1m price grid (gaps = no prints)
buy, sell, vol, n, bb, bs, pv = (OF[c].values for c in ("buy", "sell", "vol", "n", "bigbuy", "bigsell", "pv"))
c = m1.close.values
atr60 = pd.Series(m1.high.values - m1.low.values).rolling(60 * 14).mean().values * np.sqrt(15)  # ~ATR of 15m bars, scale only
cs = lambda x: np.r_[0, np.cumsum(x)]
CB, CS, CV, CN, CBB, CBS, CPV = map(cs, (buy, sell, vol, n, bb, bs, pv))
SIG = lab.SIG; mi = SIG.m1.values; dirn = SIG.dir.values
def win(C, k): j = mi + 1; return C[j] - C[np.maximum(j - k, 0)]
F = pd.DataFrame(index=SIG.index)
for k in (5, 15, 60, 240, 1440):
    v = np.maximum(win(CV, k), 1)
    F[f"of_delta{k}"] = (win(CB, k) - win(CS, k)) / v * dirn                       # aggressive buy minus sell share, with the trade
    F[f"of_bigdelta{k}"] = (win(CBB, k) - win(CBS, k)) / v * dirn                   # large-print imbalance
    F[f"of_bigshare{k}"] = (win(CBB, k) + win(CBS, k)) / v                          # share of volume from large prints
    ret = (c[mi] - c[np.maximum(mi - k, 0)]) / atr60[mi]
    F[f"of_ret{k}"] = ret * dirn
    F[f"of_absorb{k}"] = np.log1p(v) - np.log1p(np.abs(ret) * 1000)                 # volume per unit of price move
    F[f"of_agree{k}"] = np.sign(F[f"of_delta{k}"]) * np.sign(F[f"of_ret{k}"])        # flow confirms the move?
volm = pd.Series(vol).rolling(1440 * 5, min_periods=1440).mean().values
for k in (5, 15, 60):
    F[f"of_volrate{k}"] = win(CV, k) / k / np.maximum(volm[mi], 1e-9)               # activity vs last 5 days
    F[f"of_size{k}"] = win(CV, k) / np.maximum(win(CN, k), 1)                       # average print size
# session VWAP (UTC day) distance, prices back-adjusted like the 1m series
day = idx.floor("D").values; first = pd.Series(np.arange(len(idx))).groupby(day).transform("min").values
vw_num = CPV[mi + 1] - CPV[first[mi]]; vw_den = CV[mi + 1] - CV[first[mi]]
vwap = vw_num / np.maximum(vw_den, 1) + G_.ADJ[mi]
F["of_vwapdist"] = (c[mi] - vwap) / atr60[mi] * dirn
# delta trend: cumulative delta slope over 60 min vs price slope (divergence when flow fades a rising price)
F["of_div60"] = F.of_delta60 - np.tanh(F.of_ret60)
F = F.replace([np.inf, -np.inf], np.nan).astype("float32")
F.to_parquet("of_features.parquet"); print(F.shape); print(F.describe().T[["mean", "std"]].round(3).head(40).to_string())
