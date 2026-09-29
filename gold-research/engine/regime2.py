import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import dyn2_run as R2
m1 = R2.m1; print(m1.columns.tolist())
d = m1.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
h4 = m1.resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def atr(b, n):
    pc = b.close.shift(); tr = np.maximum(b.high - b.low, np.maximum((b.high - pc).abs(), (b.low - pc).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean()
def rpct(s, n):  # rolling percentile of the current value vs its own past n values (known at time)
    return s.rolling(n, min_periods=n // 2).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)
F = pd.DataFrame(index=d.index)
F["d_trend"] = rpct((d.close - d.close.ewm(span=50, adjust=False).mean()).abs() / atr(d, 14), 250)
F["d_volx"] = rpct(atr(d, 5) / atr(d, 50), 250)
F["d_er"] = rpct((d.close - d.close.shift(10)).abs() / d.close.diff().abs().rolling(10).sum(), 250)
G = pd.DataFrame(index=h4.index)
G["h4_er"] = rpct((h4.close - h4.close.shift(30)).abs() / h4.close.diff().abs().rolling(30).sum(), 750)
G["h4_volx"] = rpct(atr(h4, 6) / atr(h4, 120), 750)
# shift: a bar's value is known at its close -> available from the next bar
F = F.shift(1); G = G.shift(1)
T = pd.read_parquet("../trades_v3.parquet")
keep = np.zeros(len(T), bool); bu = {}
for i, (s, a, b) in enumerate(zip(T.slot, T.t_in, T.t_out)):
    if bu.get(s, -1) < a: keep[i] = True; bu[s] = b
t = T.time.dt.floor("1D"); t4 = T.time.dt.floor("4h")
for c in F: T[c] = F[c].reindex(pd.DatetimeIndex(t)).values
for c in G: T[c] = G[c].reindex(pd.DatetimeIndex(t4)).values
T.to_parquet("../trades_v3_reg.parquet")
X = T[keep]
for c in list(F) + list(G) + ["edge"]:
    q = pd.qcut(X[c], 5, labels=False, duplicates="drop")
    g = X.groupby(q).R.agg(["mean", "count"]); w = X.groupby(q).R.apply(lambda r: (r > 0).mean())
    print(f"{c:8s} meanR by quintile: {np.round(g['mean'].values, 2)}  win%: {np.round(w.values * 100)}")
