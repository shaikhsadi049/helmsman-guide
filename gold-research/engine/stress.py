import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import dyn_run as DR, adv3 as D, adv as A, gcdata as G_, adv_run as AR
idx = AR.m1.index; S25 = DR.S25
picks = pickle.load(open("dyn_picks.pkl", "rb"))
PREP = {int(r.es): DR.prep(int(r.es)) for r in picks}
def run(cost, delay=0):
    T = []
    for r in picks:
        tf, E = PREP[int(r.es)]; G = AR.GR[tf]
        k = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mae_a"], int(r.lb), r.qsl, 2.0), 0.5, 8.0); risk = k * E["atr"]
        r1 = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mfe_a"], int(r.lb), r.qtp, 1.0) / k, 0.2, 3.0)
        tw = DR.trail_quantile(E["m1"], r.qtr) * E["atr4"]
        ent = E["m1"].astype(np.int64) + delay        # entry `delay` minutes late (levels still from signal close)
        res = D.sim_dyn(ent, E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c,
                        DR.G4.mgmt, DR.G4.trend_up, DR.G4.trend_dn, 0.5, r.lock, bool(r.brk), cost, 60 * 24 * 30)
        live = np.where(idx[E["m1"]] >= S25)[0]; take = A.greedy(ent[live], res[live, 2].astype(np.int64)); s = live[take]
        T.append(pd.DataFrame(dict(R=res[s, 0], usd=res[s, 0] * risk[s], q=idx[E["m1"][s]].to_period("Q").astype(str))))
    T = pd.concat(T); w = T.R > 0; q = T.groupby("q").R.sum()
    eq = T.R.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    return f"trades {len(T)} win {w.mean()*100:.0f}% PF {T.R[w].sum()/-T.R[~w].sum():.2f} totR {T.R.sum():+.1f} DD {dd:.1f}R quarters+ {(q>0).sum()}/{len(q)} | 0.01 lot ${T.usd.sum():+.0f}"
for c in (0.34, 0.6, 1.0, 1.5, 2.5):
    print(f"cost ${c:.2f}/oz round trip : {run(c)}")
for dl in (1, 5):
    print(f"entry {dl} min late, cost $0.60 : {run(0.6, dl)}")
