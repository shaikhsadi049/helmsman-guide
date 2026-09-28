import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import adv_run as AR, adv as A, gcdata as G_
both = pd.read_parquet("both_years.parquet")
cat = {
 "H1  1h high-win":  both[(both.tf == "1h") & (both.pfmin >= 1.5) & (both.winmin >= 60)],
 "RN5 5m runner":    both[(both.tf == "5min") & (both.pfmin >= 2)],
 "RN15 15m runner":  both[(both.tf == "15min") & (both.pfmin >= 2)],
}
PERIODS = [("BLIND 2023-03..2024-07", "2023-03-01", "2024-08-01"), ("Y1 2024-08..2025-07", "2024-08-01", "2025-08-01"), ("Y2 2025-08..2026-07", "2025-08-01", "2026-08-01")]
def trades(r):
    tf, entry, pb, conf, ar, sess = AR.ENTRY_SETS[int(r.es)]
    out = []
    for G in AR.GR.values(): G.trade_ok = AR.m1.index >= pd.Timestamp("2023-03-01", tz="UTC")
    E = AR.entry_set(tf, entry, pb, conf, ar, sess)
    o = np.argsort(E["m1"], kind="stable"); E = {k: v[o] for k, v in E.items()}
    risk = E["atr"] * r.k * ((0.7 + 0.6 * E["volp"]) if r.adapt else 1.0)
    G = AR.GR[tf]; T = G if r.ttf == "same" else AR.GR[r.ttf]
    res = A.sim(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1,
                T.trend_up, T.trend_dn, r.r1, r.f1, r.lock, r.trail, bool(r.brk), r.gb_a, r.gb_g, G_.COST_RT, 60 * 24 * 15)
    take = A.greedy(E["m1"], res[:, 2].astype(np.int64))
    return pd.DataFrame(dict(t_in=AR.m1.index[E["m1"][take]], t_out=AR.m1.index[res[take, 2].astype(int)], R=res[take, 0]))
def rep(t, label):
    print(label)
    for nm, a, b in PERIODS:
        m = (t.t_in >= pd.Timestamp(a, tz="UTC")) & (t.t_in < pd.Timestamp(b, tz="UTC"))
        R = t.R[m].values
        if len(R) == 0: print(f"   {nm}: none"); continue
        w = R > 0; eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
        mo = t[m].groupby(t.t_out[m].dt.strftime("%Y-%m")).R.sum()
        print(f"   {nm}: n={len(R):3d} win={w.mean()*100:3.0f}% PF={R[w].sum()/-R[~w].sum():.2f} totR={R.sum():+7.1f} DD={dd:5.1f}R months+={(mo>0).mean()*100:3.0f}% bigWin={R.max():.1f}R")
T = {}
for name, c in cat.items():
    r = c.sort_values("rdd", ascending=False).iloc[0]
    tf, entry, pb, conf, ar, sess = AR.ENTRY_SETS[int(r.es)]
    desc = f"{tf} {entry}{pb if entry=='pullback' else ''} conf={'+'.join(conf) or '-'} adx={ar} sess={sess} SL={r.k}ATR{'(vol-adaptive)' if r.adapt else ''} TP1={r.r1}R x{r.f1} lock={r.lock} runner: {r.ttf} trail={r.trail} brk={r.brk} gb={r.gb_a}/{r.gb_g}"
    T[name] = trades(r); rep(T[name], f"\n{name}: {desc}")
allt = pd.concat(T.values()).sort_values("t_out")
rep(allt, "\n>>> CHAMPION PORTFOLIO (H1 + RN5 + RN15)")
allt.to_csv("champion_trades.csv", index=False)
