import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import mr as M, dyn2_run as R2, adv3 as D, adv4, adv as A, gcdata as G_
idx = R2.idx
def run_mean(tf, fam, regime, sess, qsl, frac, cost=G_.COST_RT):
    E = M.entries(tf, fam, regime, sess); G = R2.GR[tf]; m = E["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, qsl, 2.0), 0.3, 8.0); risk = k * E["atr"]
    ma = G.bars.close.rolling(20).mean().values
    bi = np.searchsorted(G.pos, m)             # TF bar index of each signal
    dist = np.abs(ma[bi] - E["lvl"]) * frac
    r1 = np.clip(dist / risk, 0.1, 5.0)
    hor = M.MRH[tf] * int(pd.Timedelta(tf).total_seconds() // 60)
    res = adv4.sim_dyn2(m, E["dir"].astype(np.int64), E["lvl"], risk, r1, np.zeros(len(m)), G.o, G.h, G.l, G.c, R2.G4.mgmt, R2.G4.trend_up, R2.G4.trend_dn, 1.0, 0.0, False, cost, hor)
    sel = np.where(idx[m] >= R2.S25)[0]; take = A.greedy(m[sel], res[sel, 2].astype(np.int64)); s = sel[take]
    return pd.DataFrame(dict(R=res[s, 0], risk=risk[s], time=idx[m[s]]))
def rep(r):
    R = r.R.values; w = R > 0; q = r.groupby(r.time.dt.tz_localize(None).dt.to_period("Q")).R.sum(); Rc = R - 1.66 / r.risk.values
    return f"n {len(R):3d} win {w.mean()*100:3.0f}% PF {R[w].sum()/-R[~w].sum():.2f} sumR {R.sum():+6.1f} q+ {(q>0).sum()}/7 cost$2 {Rc.sum():+6.1f}"
for spec in [("15min", "rsi2", "no4h", True), ("1h", "z2", "no4h", False), ("30min", "z2.5", "no4h", False), ("1h", "fbo", "no4h", True)]:
    print(spec)
    for qtp in (0.3, 0.5, 0.7): print(f"   quantile TP q{qtp}:  " + rep(M.run(*spec, .7, qtp)))
    for frac in (0.5, 1.0, 1.5): print(f"   mean target x{frac}:  " + rep(run_mean(*spec, .7, frac)))
