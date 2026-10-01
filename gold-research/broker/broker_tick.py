"""BROKER verification: every exit of findings 42-47 and today's Assay re-simulated on real XAUUSD bid/ask ticks (HistData feed).
Longs: entry at ASK, stop/TP/trail on BID.  Shorts: entry at BID, stop/TP/trail on ASK.  + $0.07/oz commission."""
import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, glob, pickle, talib, warnings; warnings.filterwarnings("ignore")
from numba import njit
import lab, gcdata as G_, dyn2_run as R2
SIG = lab.SIG; F = lab.load_F(); M1 = SIG.m1.values; idx = R2.idx
code = open("../lab/outcomes.py").read()
s1 = code.index("@njit(cache=True)\ndef sim_one"); s2 = code.index("@njit(parallel=True")
exec(code[s1:s2].replace("@njit(cache=True)", "@njit"))
ns = {}
pre = code.split("# ---------------- policy grid")[0].replace("@njit(cache=True)", "@njit").replace("@njit(parallel=True, cache=True)", "@njit(parallel=True)")
mid = code.split('print("policies:", len(P), flush=True)')[1].split("R = np.full((n, len(P))")[0]
pre = pre.replace("pd.read_parquet(\"signals.parquet\")", "pd.read_parquet(\"../lab/signals.parquet\")"); exec(compile(pre, "o_pre", "exec"), ns); ns["P"] = lab.P; exec(compile(mid, "o_mid", "exec"), ns)
POL = lab.P
def T(sq, tp, part, be, trail, rat, ts): return lab.policy_index(kind="trend", sq=sq, tp=tp, part=part, be=be, trail=trail, rat=rat, ts=ts)[0]
def Fd(sq, tp, be, rat, hm): return lab.policy_index(kind="fade", sq=sq, tp=tp, be=be, rat=rat, hm=hm)[0]
REC = {"S1": [T("k70","none","slot","none","h4q80","none","none"), T("k70","none","none","be1","h4q80","none","none")],
 "S2": [T("k50","3R","none","be1","h4q80","q90k50","ts_half"), T("k50","3R","none","be1","h4q80","q70k50","ts_half")],
 "S3": [T("k70","3R","slot","none","h4q50","none","none")], "S4": [T("k70","none","none","none","atr4","none","none")],
 "S5": [lab.baseline_policy("S5")], "S6": [T("k70","3R","none","be1","h4q80","none","none")],
 "S7": [T("k50","none","none","none","h4q80","q90k50","none")], "F8": [Fd("k50","f50","none","none",1.0)],
 "F9": [Fd("k70","f70","be1","none",2.0)], "F10": [Fd("k70","mean","none","none",1.0)], "F11": [lab.baseline_policy("F11")]}
# ---- ticks
fs = sorted(glob.glob("../hdt/*.parquet"), key=lambda f: tuple(int(x) for x in f.split("/")[-1][:-8].split("_")))
tk = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
ts = tk.time.values.astype("datetime64[ns]").astype(np.int64); o = np.argsort(ts, kind="stable"); ts = ts[o]
BID = tk.bid.values[o].astype(np.float64); ASK = tk.ask.values[o].astype(np.float64); del tk
bad = (ASK - BID) <= 0; ASK[bad] = BID[bad] + 0.3
m1ns = idx.values.astype("datetime64[ns]").astype(np.int64)
mi = np.clip(np.searchsorted(m1ns, ts, side="right") - 1, 0, len(idx) - 1)
h4c = np.zeros(len(ts), np.bool_); end4 = (R2.G4.bars.index + pd.Timedelta("4h")).values.astype("datetime64[ns]").astype(np.int64)
p4 = np.searchsorted(ts, end4, side="left") - 1; h4c[p4[p4 >= 0]] = True
print("ticks", len(ts), flush=True)
G4 = R2.GR["4h"]; atr4w = talib.ATR(G4.bars.high.values, G4.bars.low.values, G4.bars.close.values, 14)
def atr4_at(m):  # last CLOSED H4 bar at 1m bar m
    j = np.searchsorted(G4.pos, m, side="right") - 1; return atr4w[np.clip(j, 0, len(atr4w) - 1)]
TEND = pd.Timestamp("2026-08-01", tz="UTC")
def sim_rows(rows, risk, tp, pf, pR, lockR, be, tkind, tw, ra, hor_min, tsT_min):
    t_sig = (idx[M1[rows]] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64)
    i0 = np.searchsorted(ts, t_sig, side="left") - 1
    R = np.full(len(rows), np.nan); X = np.zeros(len(rows), np.int64)
    for k, r in enumerate(rows):
        if i0[k] < 0 or i0[k] + 2 >= len(ts): continue
        d = int(SIG.dir.values[r]); path = BID if d == 1 else ASK
        hk = int(np.searchsorted(ts, t_sig[k] + int(hor_min[k]) * 60 * 10**9) - i0[k])
        tsk = int(np.searchsorted(ts, t_sig[k] + int(tsT_min[k]) * 60 * 10**9) - i0[k]) if tsT_min is not None else 0
        rr, x, mf, lk = sim_one(i0[k], d, SIG.lvl.values[r], risk[k], tp[k], pf, pR[k], lockR, be[0], be[1], tkind, tw[k], ra[k], 0.5,
                                tsk, 0.0, max(hk, 1), path, path, path, path, h4c, G_.COST_RT)
        spread = ASK[i0[k] + 1] - BID[i0[k] + 1]
        R[k] = rr - spread / risk[k]; X[k] = mi[min(x, len(mi) - 1)]
    return R, X
def pol_RX(rows, j):
    sel = np.zeros(len(SIG), bool); sel[rows] = True
    risk, tp, pf, pR, lockR, be, tkind, tw, ra, hor, tsTv = ns["arrays"](POL[j], sel)
    return sim_rows(rows, risk, tp, pf, pR, lockR, be, tkind, tw, ra, hor, tsTv)
def legs_RX(rows, legs):
    rs = [pol_RX(rows, j) for j in legs]; return np.mean([r[0] for r in rs], 0), np.max([r[1] for r in rs], 0)
def past_rank(x):
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        p = x[:i]; p = p[np.isfinite(p)]
        if len(p) >= 50 and np.isfinite(x[i]): out[i] = (p < x[i]).mean()
    return out
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
OUT = {}
for slot in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "F8", "F9", "F10", "F11"]:
    allr = np.where(SIG.slot.values == slot)[0]; live = (lab.TIME[allr] >= lab.D0) & (lab.TIME[allr] < pd.Timestamp("2026-09-01", tz="UTC"))
    rows = allr[live]; res = {"rows": rows}
    res["today"] = legs_RX(rows, [lab.baseline_policy(slot)])
    res["rec"] = legs_RX(rows, REC[slot])
    if slot.startswith("S"):
        s = SIG.iloc[rows]; k = np.clip(s[SQ[slot]].values, 0.5, 8.0); risk = k * s.atr.values; n = len(rows)
        # market-measured TP: q0.85 of PAST resolved signals' MFE/k (all slot signals incl. 2024 warm-up)
        sa = SIG.iloc[allr]; ka = np.clip(sa[SQ[slot]].values, 0.5, 8.0); mfeR = sa.mfe_a.values / ka; xend = sa.xend.values; ma = M1[allr]
        tpa = np.full(len(allr), 3.0)
        for i in range(len(allr)):
            past = xend[:i] < ma[i]
            if past.sum() >= 30: tpa[i] = np.quantile(mfeR[:i][past], 0.85)
        tpq = np.clip(tpa, 0.5, 8.0)[live]
        hor = np.full(n, 14400); z = np.zeros(n); one = np.ones(n) * 99.0
        res["A3"] = sim_rows(rows, risk, np.full(n, 3.0), 0.0, one, 0.0, (1.0, 0.05), 0, z, z, hor, None)
        res["Aq85"] = sim_rows(rows, risk, tpq, 0.0, one, 0.0, (1.0, 0.05), 0, z, z, hor, None)
        res["B"] = sim_rows(rows, risk, z, 0.0, one, 0.0, (1.0, 0.05), 2, 1.5 * atr4_at(s.m1.values), z, hor, None)
        res["adx_bad"] = np.nan_to_num(past_rank(F.h1_adx.values[allr]), nan=0)[live] > 0.8
        res["h4_bad"] = F.h4_stack.values[rows] != 1
    OUT[slot] = res
    msg = []
    for name in [k for k in ("today", "rec", "A3", "Aq85", "B") if k in res]:
        R, X = res[name]; w = rows[lab.TIME[rows] < TEND]; nw = len(w)
        tk_ = lab.greedy(w, X[:nw]); m = lab.metrics(R[:nw][tk_], lab.TIME[w[tk_]])
        msg.append(f"{name} {m['sumR']:+.1f}R dd{m['maxDD_R']:.1f} m+{m['months_pos']}")
    print(slot, " | ".join(msg), flush=True)
    pickle.dump(OUT, open("broker_tick.pkl", "wb"))
