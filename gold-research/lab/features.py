"""LAB step 2: causal market-behaviour features at every signal (only bars CLOSED before the signal is known)."""
import sys; sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import dyn2_run as R2
idx = R2.idx; m1 = R2.m1
SIG = pd.read_parquet("signals.parquet")
t_known = (idx[SIG.m1.values] + pd.Timedelta(minutes=1)).values   # signal is known at the end of its minute
def wilder(x, n): return x.ewm(alpha=1 / n, adjust=False).mean()
def atr(b, n=14):
    pc = b.close.shift(); tr = np.maximum(b.high - b.low, np.maximum((b.high - pc).abs(), (b.low - pc).abs())); return wilder(tr, n)
def rsi(c, n):
    d = c.diff(); u = wilder(d.clip(lower=0), n); v = wilder((-d).clip(lower=0), n); return 100 - 100 / (1 + u / v.replace(0, np.nan))
def adx(b, n=14):
    up = b.high.diff(); dn = -b.low.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0); ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(b, n); pdi = 100 * wilder(pd.Series(pdm, b.index), n) / a; ndi = 100 * wilder(pd.Series(ndm, b.index), n) / a
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan); return wilder(dx, n), pdi - ndi
def prank(s, n): return s.rolling(n, min_periods=n // 3).rank(pct=True)
def tf_feats(b, p):
    """b: OHLCV bars of one timeframe; p: prefix. Directional features are signed later."""
    f = pd.DataFrame(index=b.index); c = b.close; a = atr(b)
    f[p + "atr_pct"] = a / c * 100; f[p + "atr_rank"] = prank(a, 250); f[p + "atr_ratio"] = atr(b, 5) / atr(b, 50)
    for n in (1, 3, 6, 12, 24, 48): f[p + f"ret{n}"] = (c - c.shift(n)) / a          # D: directional
    for n in (10, 30): f[p + f"er{n}"] = (c - c.shift(n)).abs() / c.diff().abs().rolling(n).sum()
    ad, di = adx(b); f[p + "adx"] = ad; f[p + "di"] = di / 100                      # di: D
    f[p + "rsi2"] = rsi(c, 2) - 50; f[p + "rsi14"] = rsi(c, 14) - 50              # D
    ma = c.rolling(20).mean(); sd = c.rolling(20).std(); f[p + "z20"] = (c - ma) / sd   # D
    f[p + "bbw_rank"] = prank(sd / ma, 250)
    E = {n: c.ewm(span=n, adjust=False).mean() for n in (20, 30, 50, 60, 100, 200)}
    bull = (E[30] > c.ewm(span=35, adjust=False).mean()) & (c.ewm(span=35, adjust=False).mean() > c.ewm(span=40, adjust=False).mean()) & \
           (c.ewm(span=40, adjust=False).mean() > c.ewm(span=45, adjust=False).mean()) & (c.ewm(span=45, adjust=False).mean() > E[50]) & (E[50] > E[60])
    bear = (E[30] < c.ewm(span=35, adjust=False).mean()) & (c.ewm(span=35, adjust=False).mean() < c.ewm(span=40, adjust=False).mean()) & \
           (c.ewm(span=40, adjust=False).mean() < c.ewm(span=45, adjust=False).mean()) & (c.ewm(span=45, adjust=False).mean() < E[50]) & (E[50] < E[60])
    f[p + "stack"] = bull.astype(float) - bear.astype(float)                        # D
    f[p + "ribbon"] = (E[30] - E[60]) / a                                           # D
    f[p + "slope50"] = (E[50] - E[50].shift(10)) / a                                # D
    f[p + "dist200"] = (c - E[200]) / a                                             # D
    f[p + "dist20"] = (c - E[20]) / a                                               # D
    hh = b.high.rolling(20).max(); ll = b.low.rolling(20).min()
    f[p + "rngpos20"] = (c - ll) / (hh - ll) - 0.5                                  # D
    f[p + "rng20_atr"] = (hh - ll) / a
    rg = (b.high - b.low); f[p + "body"] = (c - b.open) / rg.replace(0, np.nan)    # D
    f[p + "bar_atr"] = rg / a
    up = (c > c.shift()).astype(int); f[p + "streak"] = up.groupby((up != up.shift()).cumsum()).cumcount().add(1) * np.where(up == 1, 1, -1)  # D
    lr = np.log(c).diff(); f[p + "vr10"] = lr.rolling(100).apply(lambda x: 0, raw=True) if False else (lr.rolling(10).sum().rolling(50).var() / (10 * lr.rolling(50).var()))
    if "volume" in b: f[p + "vol_ratio"] = b.volume / b.volume.rolling(20).mean(); f[p + "vol_rank"] = prank(b.volume, 250)
    f[p + "nr7"] = (rg <= rg.rolling(7).min()).astype(float)
    return f
DIRS = ("ret", "di", "rsi2", "rsi14", "z20", "stack", "ribbon", "slope50", "dist200", "dist20", "rngpos20", "body", "streak")
def bars(rule):
    return m1.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
out = pd.DataFrame(index=SIG.index)
for rule, p in (("5min", "m5_"), ("15min", "m15_"), ("1h", "h1_"), ("4h", "h4_"), ("1D", "d1_")):
    b = bars(rule); f = tf_feats(b, p)
    close_t = (b.index + pd.Timedelta(rule)).values
    j = np.searchsorted(close_t, t_known, side="right") - 1                         # last bar closed by the signal time
    vals = f.values[np.clip(j, 0, len(f) - 1)]; vals[j < 0] = np.nan
    out = out.join(pd.DataFrame(vals, columns=f.columns, index=SIG.index))
    print(rule, f.shape[1], flush=True)
# daily context: today so far, prior day, gap, weekly
d = bars("1D"); da = atr(d)
day_start = pd.DatetimeIndex(t_known).floor("D")
cm = m1.close.values; tk = pd.DatetimeIndex(t_known)
mi = SIG.m1.values
dprev = np.searchsorted((d.index + pd.Timedelta("1D")).values, t_known, side="right") - 1
ph, pl, pc_, pa = d.high.values[dprev], d.low.values[dprev], d.close.values[dprev], da.values[dprev]
# today's high/low so far from 1m
day_id = idx.floor("D").values
first_of_day = pd.Series(np.arange(len(idx))).groupby(day_id).transform("min").values
hmax = pd.Series(m1.high.values).groupby(day_id).cummax().values; lmin = pd.Series(m1.low.values).groupby(day_id).cummin().values
c_now = cm[mi]
out["day_rng_atr"] = (hmax[mi] - lmin[mi]) / pa
out["day_pos"] = (c_now - lmin[mi]) / np.maximum(hmax[mi] - lmin[mi], 1e-9) - 0.5          # D
out["day_ret_atr"] = (c_now - m1.open.values[first_of_day[mi]]) / pa                       # D
out["prev_rng_atr"] = (ph - pl) / pa
out["dist_prev_hi"] = (c_now - ph) / pa; out["dist_prev_lo"] = (c_now - pl) / pa            # D
out["gap_atr"] = (m1.open.values[first_of_day[mi]] - pc_) / pa                              # D
out["hour"] = tk.hour + tk.minute / 60; out["wday"] = tk.dayofweek
out["min_since_day_open"] = (mi - first_of_day[mi])
# realised 1m volatility now vs typical for this hour (activity burst)
r1m = pd.Series(np.log(cm)).diff().abs()
out["vol60_vs_day"] = (r1m.rolling(60).mean() / r1m.rolling(1440).mean()).values[mi]
# DXY daily (from saved research file, known at previous close)
try:
    dx = pd.read_csv("../../../../../home/user/helmsman-guide/gold-research/results/dxy_daily.csv", index_col=0, parse_dates=True).iloc[:, 0]
except Exception:
    dx = pd.read_csv("/home/user/helmsman-guide/gold-research/results/dxy_daily.csv", index_col=0, parse_dates=True).iloc[:, 0]
dx.index = pd.DatetimeIndex(dx.index).tz_localize("UTC") if dx.index.tz is None else dx.index
e20 = dx.ewm(span=20, adjust=False).mean(); e50 = dx.ewm(span=50, adjust=False).mean()
dxf = pd.DataFrame({"dxy_trend": np.sign(e20 - e50), "dxy_ret5": dx.pct_change(5) * 100, "dxy_z20": (dx - dx.rolling(20).mean()) / dx.rolling(20).std()})
jd = np.searchsorted((dx.index + pd.Timedelta("1D")).values, t_known, side="right") - 1
out[["dxy_trend", "dxy_ret5", "dxy_z20"]] = dxf.values[np.clip(jd, 0, len(dxf) - 1)]
# sign directional features by trade direction ("with the trade" = positive)
dsign = SIG.dir.values
for c in out.columns:
    base = c.split("_", 1)[1] if c[:3] in ("m5_", "h1_", "h4_", "d1_") or c.startswith("m15_") else c
    if any(base.startswith(x) for x in DIRS) or c in ("day_pos", "day_ret_atr", "dist_prev_hi", "dist_prev_lo", "gap_atr", "dxy_trend", "dxy_ret5", "dxy_z20"):
        out[c] = out[c] * dsign * (-1 if c.startswith("dxy") else 1)   # dollar up is against a gold long
out = out.astype("float32")
out.to_parquet("features.parquet")
print("features:", out.shape, "nan share:", round(float(out.isna().mean().mean()), 3))
