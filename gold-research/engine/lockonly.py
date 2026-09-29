import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import dyn_run as DR, adv3 as D, adv as A, gcdata as G_, adv_run as AR
idx = AR.m1.index; S25 = DR.S25
top = pd.read_parquet("dyn_top.parquet"); U = pd.concat([g[g.qtp > 0].head(60) for _, g in top.groupby("tf")])
PREP = {}
def run(r, f1):
    es = int(r.es)
    if es not in PREP: PREP[es] = DR.prep(es)
    tf, E = PREP[es]; G = AR.GR[tf]
    k = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mae_a"], int(r.lb), r.qsl, 2.0), 0.5, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mfe_a"], int(r.lb), r.qtp, 1.0) / k, 0.2, 3.0)
    tw = DR.trail_quantile(E["m1"], r.qtr) * E["atr4"] if r.qtr > 0 else np.zeros(len(risk))
    res = D.sim_dyn(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c,
                    DR.G4.mgmt, DR.G4.trend_up, DR.G4.trend_dn, f1, r.lock, bool(r.brk), G_.COST_RT, 60 * 24 * 30)
    live = np.where(idx[E["m1"]] >= S25)[0]; take = A.greedy(E["m1"][live], res[live, 2].astype(np.int64)); s = live[take]
    R = res[s, 0]; q = pd.Series(R).groupby(idx[E["m1"][s]].to_period("Q").astype(str)).sum()
    eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    return R.sum(), (R > 0).mean() * 100, dd, (q > 0).all()
rows = []
for _, r in U.iterrows():
    a = run(r, 0.5); b = run(r, 1e-9)
    rows.append((r.tf, r.lock) + a + b)
X = pd.DataFrame(rows, columns=["tf", "lock", "R_half", "win_half", "dd_half", "allq_half", "R_lock", "win_lock", "dd_lock", "allq_lock"])
X.to_csv("lockonly.csv", index=False)
for (tf, lk), g in X.groupby(["tf", "lock"]):
    print(f"{tf:5s} lock={lk} n={len(g)} | lock-only better in {np.mean(g.R_lock > g.R_half)*100:.0f}% | median R {g.R_half.median():+.1f} -> {g.R_lock.median():+.1f} | win {g.win_half.median():.0f}% -> {g.win_lock.median():.0f}% | DD {g.dd_half.median():.1f} -> {g.dd_lock.median():.1f} | R/DD {np.median(g.R_half/g.dd_half.clip(lower=1)):.1f} -> {np.median(g.R_lock/g.dd_lock.clip(lower=1)):.1f} | all-quarters+ {g.allq_half.mean()*100:.0f}% -> {g.allq_lock.mean()*100:.0f}%")
