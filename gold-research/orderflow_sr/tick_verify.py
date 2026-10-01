"""Tick-by-tick verification of today's exit vs the lab recommendation for every slot (2025+, one position per slot)."""
import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from numba import njit
import lab, gcdata as G_, ticks as TK, dyn2_run as R2
src = open("../lab/portfolio.py").read().split('if __name__ == "__main__":')[0]; P = {}; exec(compile(src, "portfolio", "exec"), P)
src2 = open("../lab/outcomes.py").read(); s1 = src2.index("@njit(cache=True)\ndef sim_one"); s2 = src2.index("@njit(parallel=True")
exec(src2[s1:s2].replace("@njit(cache=True)", "@njit"))       # same simulator as the lab, run on the tick path
tk = TK.load_ticks("2024-12-15"); ts = tk.ts_event.values.astype("datetime64[ns]").astype(np.int64)
idx = R2.idx; m1ns = idx.values.astype("datetime64[ns]").astype(np.int64)
mi = np.clip(np.searchsorted(m1ns, ts, side="right") - 1, 0, len(idx) - 1); p = tk.price.values + G_.ADJ[mi]; del tk
h4c = np.zeros(len(p), np.bool_); end4 = (R2.G4.bars.index + pd.Timedelta("4h")).values.astype("datetime64[ns]").astype(np.int64)
tp4 = np.searchsorted(ts, end4, side="left") - 1; h4c[tp4[tp4 >= 0]] = True
print("ticks", len(p), flush=True)
SIG = lab.SIG; POL = lab.P
def run_policy(rows, j):
    """re-simulate lab policy j for these signals on ticks (same parameters the lab used)"""
    pdict = POL[j]; sel = np.zeros(len(SIG), bool); sel[rows] = True
    # rebuild the arrays outcomes.py used, for exactly these rows
    ns = {}; exec(compile(open("../lab/outcomes.py").read().split("R = np.full((n, len(P))")[0].split("print(\"policies:\"")[1].split("\n", 1)[1], "o", "exec"), ns_glob, ns) if False else None
    return None
# simpler: re-derive parameters with the lab's own arrays() helper
ns = {}; code = open("../lab/outcomes.py").read()
pre = code.split("# ---------------- policy grid")[0].replace("@njit(cache=True)", "@njit").replace("@njit(parallel=True, cache=True)", "@njit(parallel=True)")
mid = code.split("print(\"policies:\", len(P), flush=True)")[1].split("R = np.full((n, len(P))")[0]
pre = pre.replace("pd.read_parquet(\"signals.parquet\")", "pd.read_parquet(\"../lab/signals.parquet\")"); exec(compile(pre, "o_pre", "exec"), ns); ns["P"] = POL; exec(compile(mid, "o_mid", "exec"), ns)
HOR_TF = ns["HOR_TF"]
def tick_R(rows, j):
    sel = np.zeros(len(SIG), bool); sel[rows] = True
    risk, tp, pf, pR, lockR, be, tkind, tw, ra, hor, tsTv = ns["arrays"](POL[j], sel)
    t_sig = (idx[SIG.m1.values[rows]] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64)
    i0 = np.searchsorted(ts, t_sig, side="left") - 1
    R = np.empty(len(rows)); X = np.empty(len(rows), np.int64)
    for k, r in enumerate(rows):
        e_ns = t_sig[k] + int(hor[k]) * 60 * 10**9; hk = int(np.searchsorted(ts, e_ns) - i0[k])
        tsk = 0
        if tsTv is not None: tsk = int(np.searchsorted(ts, t_sig[k] + int(tsTv[k]) * 60 * 10**9) - i0[k])
        rr, x, mf, lk = sim_one(i0[k], int(SIG.dir.values[r]), SIG.lvl.values[r], risk[k], tp[k], pf, pR[k], lockR, be[0], be[1], tkind, tw[k], ra[k], 0.5,
                                tsk, 0.0, max(hk, 1), p, p, p, p, h4c, G_.COST_RT)
        R[k] = rr; X[k] = mi[min(x, len(mi) - 1)]
    return R, X
out = []
for slot, (legs, w) in P["REC"].items():
    rows = np.where((SIG.slot.values == slot) & (lab.TIME >= lab.D0))[0]
    keep = P["skip_mask"](slot, np.where(SIG.slot.values == slot)[0])[-len(rows):]
    for name, L in (("today", [lab.baseline_policy(slot)]), ("recommended", legs)):
        k = keep if name == "recommended" else np.ones(len(rows), bool)
        res = {}
        for mode in ("1m", "tick"):
            if mode == "1m":
                Rv = np.mean([np.asarray(lab.load_R()[rows, j]) for j in L], 0); Xv = np.max([np.asarray(lab.load_X()[rows, j]) for j in L], 0)
            else:
                rs = [tick_R(rows, j) for j in L]; Rv = np.mean([r[0] for r in rs], 0); Xv = np.max([r[1] for r in rs], 0)
            rr = rows[k]; tk_ = lab.greedy(rr, Xv[k]); m = lab.metrics(Rv[k][tk_], lab.TIME[rr[tk_]]); res[mode] = m
        print(f"{slot:4s} {name:12s} 1m: {res['1m']['sumR']:+6.1f}R PF {res['1m']['PF']:.2f} DD {res['1m']['maxDD_R']:4.1f} | tick: {res['tick']['sumR']:+6.1f}R PF {res['tick']['PF']:.2f} DD {res['tick']['maxDD_R']:4.1f} m+ {res['tick']['months_pos']}", flush=True)
        out.append(dict(slot=slot, spec=name, **{f"{a}_{b}": res[a][b] for a in res for b in ("sumR", "PF", "maxDD_R", "months_pos", "eq_R2")}))
pd.DataFrame(out).to_csv("tick_verify.csv", index=False)
