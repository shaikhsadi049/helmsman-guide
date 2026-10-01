"""Support/resistance and supply/demand features at every lab signal (causal: only bars closed before the signal).
All distances in units of the trade's own stop R where it matters ("room"), else ATR. Signed so that 'room' = space in the
trade direction before the next opposing level, 'behind' = distance to the nearest level behind the trade (support for a long)."""
import sys; sys.path.insert(0, "../bt"); sys.path.insert(0, "../lab")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import gcdata as G_, lab
m1 = G_.load_1m(); idx = m1.index; SIG = lab.SIG
t_known = (idx[SIG.m1.values] + pd.Timedelta(minutes=1)).values
price = m1.close.values[SIG.m1.values]; dirn = SIG.dir.values
kcol = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
risk = np.array([SIG[kcol.get(s, "k70")].values[i] for i, s in enumerate(SIG.slot.values)]) * SIG.atr.values
risk = np.maximum(risk, 1e-6)
def bars(rule): return m1.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
def atr(b, n=14):
    pc = b.close.shift(); tr = np.maximum(b.high - b.low, np.maximum((b.high - pc).abs(), (b.low - pc).abs())); return tr.rolling(n).mean()
F = pd.DataFrame(index=SIG.index)
# ---- 1) swing pivots (fractals): a high with k lower highs on each side; confirmed only k bars later (causal)
def pivots(rule, k, lookback):
    b = bars(rule); h, l = b.high.values, b.low.values; n = len(b)
    ph = np.zeros(n, bool); pl = np.zeros(n, bool)
    for i in range(k, n - k):
        if h[i] == h[i - k:i + k + 1].max(): ph[i] = True
        if l[i] == l[i - k:i + k + 1].min(): pl[i] = True
    conf_t = (b.index + pd.Timedelta(rule) * (k + 1)).values      # known when k more bars have closed
    H = pd.DataFrame({"t": conf_t[ph], "lvl": h[ph]}); L = pd.DataFrame({"t": conf_t[pl], "lvl": l[pl]})
    a = atr(b).values; at = (b.index + pd.Timedelta(rule)).values
    return H, L, a, at, lookback
for rule, k, lb in (("1h", 3, pd.Timedelta("10D")), ("4h", 3, pd.Timedelta("40D")), ("1D", 2, pd.Timedelta("250D"))):
    H, L, a, at, lb = pivots(rule, k, lb); p = rule.lower()
    ja = np.clip(np.searchsorted(at, t_known, side="right") - 1, 0, len(a) - 1); A = a[ja]
    room = np.full(len(SIG), np.nan); behind = np.full(len(SIG), np.nan); touches = np.full(len(SIG), np.nan); bstr = np.full(len(SIG), np.nan)
    Ht, Hl, Lt, Ll = H.t.values, H.lvl.values, L.t.values, L.lvl.values
    for i in range(len(SIG)):
        t = t_known[i]; t0 = t - lb.to_timedelta64()
        hs = Hl[(Ht <= t) & (Ht >= t0)]; ls = Ll[(Lt <= t) & (Lt >= t0)]; levels = np.r_[hs, ls]
        if len(levels) == 0: continue
        px = price[i]; d = dirn[i]
        ahead = levels[(levels - px) * d > 0]; back = levels[(levels - px) * d <= 0]
        if len(ahead): nxt = ahead[np.argmin(np.abs(ahead - px))]; room[i] = abs(nxt - px) / risk[i]; touches[i] = (np.abs(levels - nxt) <= 0.25 * A[i]).sum()
        if len(back): bk = back[np.argmin(np.abs(back - px))]; behind[i] = abs(px - bk) / A[i]; bstr[i] = (np.abs(levels - bk) <= 0.25 * A[i]).sum()
    F[f"sr_room_{p}"] = room; F[f"sr_touch_ahead_{p}"] = touches; F[f"sr_behind_{p}"] = behind; F[f"sr_touch_behind_{p}"] = bstr
    print("pivots", rule, flush=True)
# ---- 2) classic levels: previous day / week high-low, pivot points, round numbers
d = bars("1D"); w = bars("1W")
def prev(b, rule):
    j = np.searchsorted((b.index + pd.Timedelta(rule)).values, t_known, side="right") - 1; return b.iloc[np.clip(j, 0, len(b) - 1)]
pd_ = prev(d, "1D"); pw = prev(w, "7D")
aD = atr(d).values[np.clip(np.searchsorted((d.index + pd.Timedelta("1D")).values, t_known, side="right") - 1, 0, len(d) - 1)]
def lvl_feats(name, hi, lo):
    up = np.where(dirn == 1, hi, lo); dn = np.where(dirn == 1, lo, hi)
    F[f"{name}_room"] = (up - price) * dirn / risk          # room to the opposing level (can be negative = already beyond)
    F[f"{name}_behind"] = (price - dn) * dirn / aD
F["pdh_beyond"] = 0.0
lvl_feats("prevday", pd_.high.values, pd_.low.values); lvl_feats("prevweek", pw.high.values, pw.low.values)
P = (pd_.high.values + pd_.low.values + pd_.close.values) / 3; R1 = 2 * P - pd_.low.values; S1 = 2 * P - pd_.high.values
lvl_feats("pivot", R1, S1); F["pivot_side"] = np.sign(price - P) * dirn
for step in (10, 50, 100):           # round numbers (price is back-adjusted, so use RAW price for round levels)
    raw = price - G_.ADJ[SIG.m1.values]
    nxt = np.where(dirn == 1, np.ceil(raw / step) * step, np.floor(raw / step) * step)
    F[f"round{step}_room"] = np.abs(nxt - raw) / risk
# ---- 3) volume profile of the previous day: POC and 70% value area (from 1m volume at close price, $1 bins)
day = idx.floor("D")
prof = pd.DataFrame({"d": day, "px": np.round(m1.close.values - G_.ADJ, 0), "v": m1.volume.values})
VP = {}
for dd, g in prof.groupby("d"):
    s = g.groupby("px").v.sum().sort_index()
    if s.sum() <= 0: continue
    poc = s.idxmax(); order = s.sort_values(ascending=False); cum = order.cumsum() / s.sum(); va = order.index[cum <= 0.7]
    VP[dd] = (poc, va.max() if len(va) else poc, va.min() if len(va) else poc)
vp = pd.DataFrame(VP, index=["poc", "vah", "val"]).T.sort_index()
jv = np.searchsorted((vp.index + pd.Timedelta("1D")).values, t_known, side="right") - 1
pv = vp.values[np.clip(jv, 0, len(vp) - 1)]; raw = price - G_.ADJ[SIG.m1.values]
F["vp_poc_dist"] = (raw - pv[:, 0]) * dirn / aD
F["vp_in_value"] = ((raw <= pv[:, 1]) & (raw >= pv[:, 2])).astype(float)
F["vp_room"] = np.where(dirn == 1, pv[:, 1] - raw, raw - pv[:, 2]) / risk
# ---- 4) supply/demand zones (H1): impulse = a bar whose body > 2 x ATR; zone = the range of the bar before it (the "base").
#      demand zone after an up-impulse, supply after a down-impulse; zone stays fresh until price trades back through it.
b = bars("1h"); a = atr(b).values; o, h, l, c = b.open.values, b.high.values, b.low.values, b.close.values; tt = (b.index + pd.Timedelta("1h")).values
zones = []   # (time known, kind +1 demand/-1 supply, top, bottom)
for i in range(1, len(b)):
    if a[i] > 0 and abs(c[i] - o[i]) > 2 * a[i]:
        zones.append((tt[i], 1 if c[i] > o[i] else -1, h[i - 1], l[i - 1]))
Z = pd.DataFrame(zones, columns=["t", "kind", "top", "bot"])
in_dem = np.zeros(len(SIG)); in_sup = np.zeros(len(SIG)); d_dem = np.full(len(SIG), np.nan); d_sup = np.full(len(SIG), np.nan)
for i in range(len(SIG)):
    t = t_known[i]; z = Z[(Z.t <= t) & (Z.t >= t - np.timedelta64(30, "D"))]
    if not len(z): continue
    px = price[i]; A = aD[i]
    dem = z[z.kind == 1]; sup = z[z.kind == -1]
    if len(dem):
        below = dem[dem.bot <= px]; 
        if len(below): j = (px - below.top).abs().idxmin(); d_dem[i] = (px - below.top[j]) / A; in_dem[i] = float(below.bot[j] <= px <= below.top[j])
    if len(sup):
        above = sup[sup.top >= px]
        if len(above): j = (above.bot - px).abs().idxmin(); d_sup[i] = (above.bot[j] - px) / A; in_sup[i] = float(above.bot[j] <= px <= above.top[j])
# signed for the trade: 'with' zone = demand for a long / supply for a short (support behind); 'against' = the opposite zone ahead
F["sd_in_with_zone"] = np.where(dirn == 1, in_dem, in_sup); F["sd_in_against_zone"] = np.where(dirn == 1, in_sup, in_dem)
F["sd_dist_with_zone"] = np.where(dirn == 1, d_dem, d_sup); F["sd_dist_against_zone"] = np.where(dirn == 1, d_sup, d_dem)
F = F.drop(columns=["pdh_beyond"]).replace([np.inf, -np.inf], np.nan).astype("float32")
F.to_parquet("sr_features.parquet"); print(F.shape); print(F.describe().T[["count", "mean", "50%"]].round(2).to_string())
