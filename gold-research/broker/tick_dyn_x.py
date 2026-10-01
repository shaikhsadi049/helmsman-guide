"""Tick verification of findings 42-44: per trend slot, A3 = TP 3R + BE1, Aq = market-measured TP (q0.85 of past MFE/k) + BE1,
B = continuous 1.5 x ATR(H4) chandelier + BE1. Also the ADX>p80 half-lot rule. Every exit simulated on every GC trade print."""
import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../bt"); sys.path.append("../mine")
import numpy as np, pandas as pd, pickle, warnings; warnings.filterwarnings("ignore")
from numba import njit
import lab, gcdata as G_, ticks as TK, dyn2_run as R2
src = open("../lab/outcomes.py").read(); s1 = src.index("@njit(cache=True)\ndef sim_one"); s2 = src.index("@njit(parallel=True")
exec(src[s1:s2].replace("@njit(cache=True)", "@njit"))
exec(open("../mine/dyn_tp.py").read().split("out = []")[0].split("SIG = lab.SIG")[1].join(["SIG = lab.SIG", ""]) if False else "")
SIG = lab.SIG; F = lab.load_F(); M1 = SIG.m1.values
def dyn_tp(rows, k, q):
    mfeR = SIG.mfe_a.values[rows] / k; xend = SIG.xend.values[rows]; m = M1[rows]; tp = np.full(len(rows), np.nan)
    for i in range(len(rows)):
        past = xend[:i] < m[i]
        if past.sum() >= 30: tp[i] = np.quantile(mfeR[:i][past], q)
    return np.clip(np.nan_to_num(tp, nan=3.0), 0.5, 8.0)
tk = TK.load_ticks("2024-12-15"); ts = tk.ts_event.values.astype("datetime64[ns]").astype(np.int64)
idx = R2.idx; m1ns = idx.values.astype("datetime64[ns]").astype(np.int64)
mi = np.clip(np.searchsorted(m1ns, ts, side="right") - 1, 0, len(idx) - 1); p = tk.price.values + G_.ADJ[mi]; del tk
h4c = np.zeros(len(p), np.bool_); print("ticks", len(p), flush=True)
DD = pickle.load(open("../mine/dyn_deep_res.pkl", "rb"))
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
# ATR(H4) Wilder on the 1m grid (as in the 1m research), value at the signal
import xexit as XE
atr4g = XE.grid("4h:atr:14")[0]
out = {}; rowsout = []
for slot in ["S2", "S3", "S4", "S6"]:
    rows = np.where((SIG.slot.values == slot))[0]; s = SIG.iloc[rows]; live = lab.TIME[rows] >= lab.D0
    k = np.clip(s[SQ[slot]].values, 0.5, 8.0); risk = k * s.atr.values
    tpq = dyn_tp(rows, k, 0.85)
    t_sig = (idx[s.m1.values] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64)
    i0 = np.searchsorted(ts, t_sig, side="left") - 1; hk = np.searchsorted(ts, t_sig + 14400 * 60 * 10**9) - i0
    specs = {"A3": (np.full(len(rows), 3.0), 0, np.zeros(len(rows))), "Aq85": (tpq, 0, np.zeros(len(rows))),
             "B": (np.zeros(len(rows)), 2, 1.5 * atr4g[s.m1.values])}
    for name, (tp, tkind, tw) in specs.items():
        R = np.full(len(rows), np.nan); X = np.zeros(len(rows), np.int64)
        for j in np.where(live)[0]:
            r, x, mf, lk = sim_one(i0[j], int(s.dir.values[j]), s.lvl.values[j], risk[j], tp[j], 0.0, 99.0, 0.0, 1.0, 0.05, tkind, tw[j], 0.0, 0.5,
                                   0, 0.0, max(int(hk[j]), 1), p, p, p, p, h4c, G_.COST_RT)
            R[j] = r; X[j] = mi[min(x, len(mi) - 1)]
        rr = rows[live]; tk_ = lab.greedy(rr, X[live]); mm = lab.metrics(R[live][tk_], lab.TIME[rr[tk_]])
        adx_bad = np.nan_to_num(DD[slot]["pr"]["ADX(H1)"], nan=0)[live][tk_] > 0.8
        mh = lab.metrics(R[live][tk_] * np.where(adx_bad, 0.5, 1.0), lab.TIME[rr[tk_]])
        out[(slot, name)] = pd.DataFrame(dict(R=R[live][tk_], w=np.where(adx_bad, 0.5, 1.0), t=lab.TIME[rr[tk_]], tx=idx[np.clip(X[live][tk_], 0, len(idx) - 1)], dir=s.dir.values[live][tk_]))
        print(f"{slot} {name:5s} tick: {mm['sumR']:+6.1f}R DD {mm['maxDD_R']:4.1f} m+ {mm['months_pos']} R2 {mm['eq_R2']} top5 {mm['top5days_pct']}% | ADX half-lot: {mh['sumR']:+6.1f}R DD {mh['maxDD_R']:4.1f} m+ {mh['months_pos']}", flush=True)
pickle.dump(out, open("tick_dyn_x.pkl", "wb"))
