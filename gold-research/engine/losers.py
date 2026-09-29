import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import dyn_run as DR, adv3 as D, adv as A, gcdata as G_, adv_run as AR, regime as RG
idx = AR.m1.index; S25 = DR.S25
picks = pickle.load(open("dyn_picks.pkl", "rb"))
rows = []
for r in picks:
    tf, E = DR.prep(int(r.es)); G = AR.GR[tf]
    k = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mae_a"], int(r.lb), r.qsl, 2.0), 0.5, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mfe_a"], int(r.lb), r.qtp, 1.0) / k, 0.2, 3.0)
    tw = DR.trail_quantile(E["m1"], r.qtr) * E["atr4"]
    res = D.sim_dyn(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c,
                    DR.G4.mgmt, DR.G4.trend_up, DR.G4.trend_dn, 0.5, r.lock, bool(r.brk), G_.COST_RT, 60 * 24 * 30)
    live = np.where(idx[E["m1"]] >= S25)[0]; take = A.greedy(E["m1"][live], res[live, 2].astype(np.int64)); s = live[take]
    er = RG.efficiency_ratio(G.bars.close, 20).values
    rows.append(pd.DataFrame(dict(tf=tf, t=idx[E["m1"][s]], R=res[s, 0], k=k[s], r1=r1[s], volp=E["volp"][s], adx=G.F.adx[E["bar"][s]], er=er[E["bar"][s]],
                                  volp4=AR.VOLP["4h"][AR.GR["4h"].idx[E["m1"][s]]], adx4=AR.GR["4h"].F.adx[AR.GR["4h"].idx[E["m1"][s]]], dir=E["dir"][s],
                                  hour=idx[E["m1"][s]].hour, trail_atr=(tw / E["atr4"])[s])))
T = pd.concat(rows)
T["bad"] = T.t.dt.strftime("%Y-%m").isin(["2026-02", "2026-03", "2026-04"])
print("mean features, losing period (Feb-Apr 2026) vs rest:")
print(T.groupby("bad")[["R", "k", "r1", "volp", "volp4", "adx", "adx4", "er", "trail_atr"]].mean().round(2).to_string())
for col in ["volp4", "k", "adx4", "er"]:
    T["b"] = pd.qcut(T[col], 4, duplicates="drop")
    print(f"\nR by quartile of {col}:"); print(T.groupby("b").R.agg(["count", "mean", "sum"]).round(2).to_string())
T.to_csv("dyn_trade_features.csv", index=False)
