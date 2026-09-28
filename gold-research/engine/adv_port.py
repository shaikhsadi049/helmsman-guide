"""Rebuild trade lists for chosen configs and combine them into a multi-timeframe portfolio."""
import pickle, numpy as np, pandas as pd
import adv_run as AR, adv as A, gcdata as G_
ES = AR.ENTRY_SETS
SPLIT = pd.Timestamp("2025-08-01", tz="UTC")

def trades(row):
    tf, entry, pb, conf, ar, sess = ES[int(row.es)]
    E = AR.entry_set(tf, entry, pb, conf, ar, sess)
    o = np.argsort(E["m1"], kind="stable")
    for k in E: E[k] = E[k][o]
    risk = E["atr"] * row.k * ((0.7 + 0.6 * E["volp"]) if row.adapt else 1.0)
    G = AR.GR[tf]; T = G if row.ttf == "same" else AR.GR[row.ttf]
    res = A.sim(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c,
                T.mgmt, T.atr1, T.trend_up, T.trend_dn, row.r1, row.f1, row.lock, row.trail, bool(row.brk),
                row.gb_a, row.gb_g, G_.COST_RT, 60 * 24 * 15)
    ex = res[:, 2].astype(np.int64)
    take = A.greedy(E["m1"], ex)
    idx = AR.m1.index
    return pd.DataFrame(dict(t_in=idx[E["m1"][take] + 1], t_out=idx[ex[take]], dir=E["dir"][take],
                             R=res[take, 0], mfe=res[take, 1], tp1=res[take, 3]))

def summary(tr, label):
    out = []
    for nm, m in (("Y1", tr.t_in < SPLIT), ("Y2", tr.t_in >= SPLIT), ("ALL", tr.t_in == tr.t_in)):
        R = tr.R[m].values
        if len(R) == 0: continue
        w = R > 0; eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
        mo = tr[m].groupby(tr.t_out[m].dt.to_period("M")).R.sum()
        out.append(f"{nm}: n={len(R)} win={w.mean()*100:.0f}% PF={R[w].sum()/-R[~w].sum():.2f} totR={R.sum():+.0f} DD={dd:.1f}R avgWin={R[w].mean():.2f}R bigWin={R.max():.1f}R months+={(mo>0).mean()*100:.0f}%")
    print(f"{label}\n   " + "\n   ".join(out))
