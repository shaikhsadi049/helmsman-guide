"""Trend flip measured on EACH STRATEGY'S OWN timeframe ladder (own TF, next, next-next): exit when it flips against the trade while open profit < th.
usage: python hold_tf.py broker|comex new|today"""
import sys, numpy as np, pandas as pd, pickle, talib, warnings; warnings.filterwarnings("ignore")
src = open("hold_study.py").read()
exec(src.split("def htf(rule):")[0])                       # data, ticks, trade source, weights
exec("def path" + src.split("def path")[1].split("PEAK = np.zeros(n)")[0].replace("", "") if False else "")
LAD = {"S1": ("30min", "1h", "4h"), "S4": ("30min", "1h", "4h"), "S2": ("15min", "1h", "4h"), "S5": ("5min", "15min", "1h"),
       "S3": ("3min", "15min", "1h"), "S6": ("3min", "15min", "1h"), "S7": ("3min", "15min", "1h")}
FLAG = {}
for rule in {r for v in LAD.values() for r in v}:
    b = m1.resample(rule, label="left", closed="left").agg({"close": "last"}).dropna(); c = b.close.values
    ct = (b.index + pd.Timedelta(rule)).values.astype("datetime64[ns]").astype(np.int64)
    e = {p: talib.EMA(c, p) for p in (20, 30, 35, 40, 45, 50, 60)}
    bull = (e[30] > e[35]) & (e[35] > e[40]) & (e[40] > e[45]) & (e[45] > e[50]) & (e[50] > e[60])
    bear = (e[30] < e[35]) & (e[35] < e[40]) & (e[40] < e[45]) & (e[45] < e[50]) & (e[50] < e[60])
    FLAG[rule] = {"x": (ct, e[20] < e[50], e[20] > e[50]), "c50": (ct, c < e[50], c > e[50]), "stack": (ct, bear, bull)}
    print("flags", rule, flush=True)
T = []
for slot, r in NEW.items():
    ok = np.isfinite(r["R"]); rr = r["rows"][ok]; t = lab.greedy(rr, r["X"][ok])
    for k in np.where(ok)[0][t]:
        row = r["rows"][k]; tin = m1ns[SIG.m1.values[row]] + 60 * 10**9; tout = m1ns[min(r["X"][k], len(m1ns) - 1)] + 60 * 10**9
        T.append(dict(slot=slot, tin=tin, tout=tout, d=int(SIG.dir.values[row]), risk=r["risk"][k], R=r["R"][k], w=W.get(slot, 1.0)))
T = pd.DataFrame(T).sort_values("tin").reset_index(drop=True); n = len(T); fin = T.R.values
s0 = np.searchsorted(ts, T.tin.values); s1 = np.searchsorted(ts, T.tout.values)
ENTRY = np.where(T.d.values == 1, ASK[np.minimum(s0, len(ts) - 1)], BID[np.minimum(s0, len(ts) - 1)])
RULES = [(lv, kind, th) for lv in (0, 1, 2) for kind in ("x", "c50", "stack") for th in (0.0, 0.5, 1.0, 99.0)]
NR = {k: fin.copy() for k in RULES}
for i in range(n):
    d = T.d.values[i]; p = BID[s0[i]:s1[i]] if d == 1 else ASK[s0[i]:s1[i]]
    if len(p) < 2: continue
    r = ((p - ENTRY[i]) * d - COST) / T.risk.values[i]; tt = ts[s0[i]:s1[i]]; lad = LAD[T.slot.values[i]]
    for (lv, kind, th) in RULES:
        ct, lb, sb = FLAG[lad[lv]][kind]; bad = lb if d == 1 else sb
        j0, j1 = np.searchsorted(ct, T.tin.values[i], side="right"), np.searchsorted(ct, T.tout.values[i], side="left")
        for k in np.where(bad[j0:j1])[0]:
            q = np.searchsorted(tt, ct[j0 + k])
            if q < len(r) and r[q] < th: NR[(lv, kind, th)][i] = r[q]; break
TEND = pd.Timestamp("2026-08-01", tz="UTC"); E0, E1 = pd.Timestamp("2026-01-26", tz="UTC"), pd.Timestamp("2026-02-04", tz="UTC")
TT = pd.to_datetime(T.tin.values, utc=True); LIVE = (TT >= lab.D0) & (TT < TEND) & ~((TT >= E0) & (TT < E1))
def rep(Rv, m):
    m = LIVE & m; d = pd.DataFrame(dict(t=TT[m], R=Rv[m] * T.w.values[m])).sort_values("t"); mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
    eq = d.R.cumsum().values; dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    return dict(R=round(eq[-1], 1), DD=round(dd, 1), mpos=int((mo > 0).sum()), sh=round(mo.mean() / mo.std(), 3))
out = []
for slot in sorted(T.slot.unique()):
    m = T.slot.values == slot; b = rep(fin, m); out.append(dict(slot=slot, tf="-", kind="hold", th=None, changed=0, **b))
    for (lv, kind, th), v in NR.items():
        out.append(dict(slot=slot, tf=LAD[slot][lv], kind=kind, th=th, changed=int(((v != fin) & m & LIVE).sum()), **rep(v, m)))
O = pd.DataFrame(out); O.to_csv(f"hold_tf_{DATA}_{SRC}.csv", index=False); print("saved", len(O))
