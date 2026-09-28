"""CHAMPION-2: all-era picks, full 2012-2026 record (2012-22 XAUUSD 15m bars; 2023-26 GC 1m)."""
import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import adv as A, gcdata as G_
import decade_grid as DG
import adv_run as AR
ok = pd.read_parquet("allera_ok.parquet")
picks = {
 "ROB-RUN15 15m swing+1H conf, runner 4H": ok[ok.tf == "15min"].sort_values("pf_min", ascending=False).iloc[0],
 "ROB-1H    1h swing, runner 4H":          ok[ok.tf == "1h"].sort_values("pf_min", ascending=False).iloc[0],
}
def decade_trades(r):
    tf, bi, d, m = DG.entries(int(r.es)); G = DG.GR[tf]
    risk = G.F.atr[bi] * r.k * ((0.7 + 0.6 * DG.VP[tf][bi]) if r.adapt else 1.0)
    T = G if r.ttf == "same" else DG.GR[r.ttf]
    res = A.sim(m.astype(np.int64), d.astype(np.int64), G.c[m], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1, T.trend_up, T.trend_dn,
                r.r1, r.f1, r.lock, r.trail, bool(r.brk), r.gb_a, r.gb_g, G_.COST_RT, 4 * 24 * 15)
    take = A.greedy(m, res[:, 2].astype(np.int64))
    return pd.DataFrame(dict(t=DG.base.index[m[take]], R=res[take, 0]))
def gc_trades(r):
    for G in AR.GR.values(): G.trade_ok = AR.m1.index >= pd.Timestamp("2023-03-01", tz="UTC")
    tf, entry, pb, conf, ar, sess = AR.ENTRY_SETS[int(r.es)]
    E = AR.entry_set(tf, entry, pb, conf, ar, sess); o = np.argsort(E["m1"], kind="stable"); E = {k: v[o] for k, v in E.items()}
    risk = E["atr"] * r.k * ((0.7 + 0.6 * E["volp"]) if r.adapt else 1.0)
    G = AR.GR[tf]; T = G if r.ttf == "same" else AR.GR[r.ttf]
    res = A.sim(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1,
                T.trend_up, T.trend_dn, r.r1, r.f1, r.lock, r.trail, bool(r.brk), r.gb_a, r.gb_g, G_.COST_RT, 60 * 24 * 15)
    take = A.greedy(E["m1"], res[:, 2].astype(np.int64))
    return pd.DataFrame(dict(t=AR.m1.index[E["m1"][take]], R=res[take, 0]))
def rep(t, label):
    t = t.copy(); t["t"] = pd.to_datetime(t.t, utc=True); t["y"] = t.t.dt.year
    R = t.R.values; w = R > 0; eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    yr = t.groupby("y").R.sum()
    print(f"{label}\n   ALL 2012-2026: n={len(R)} win={w.mean()*100:.0f}% PF={R[w].sum()/-R[~w].sum():.2f} totR={R.sum():+.0f} maxDD={dd:.0f}R  years+ {(yr>0).sum()}/{len(yr)}")
    print("   per year R: " + " ".join(f"{y}:{v:+.0f}" for y, v in yr.items()))
allt = []
for name, r in picks.items():
    t = pd.concat([decade_trades(r), gc_trades(r)]).sort_values("t"); allt.append(t)
    rep(t, name)
rep(pd.concat(allt).sort_values("t"), "\n>>> CHAMPION-2 (both)")
pd.concat(allt).to_csv("champion2_trades.csv", index=False)
pickle.dump(picks, open("champion2_picks.pkl", "wb"))
