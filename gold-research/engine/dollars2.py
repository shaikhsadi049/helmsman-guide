import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import adv as A, gcdata as G_, adv_run as AR
P = pickle.load(open("champion2_picks.pkl", "rb"))
Y26 = pd.Timestamp("2026-01-01", tz="UTC")
idx = AR.m1.index; sel = idx >= Y26
for tf in ("15min", "1h", "4h"):
    G = AR.GR[tf]; a = pd.Series(G.atr1[sel])
    print(f"2026 ATR({tf}) median ${a.median():.1f}  (range 10-90%: ${a.quantile(.1):.1f} - ${a.quantile(.9):.1f})")
allt = []
for name, r in P.items():
    for G in AR.GR.values(): G.trade_ok = idx >= pd.Timestamp("2023-03-01", tz="UTC")
    tf, entry, pb, conf, ar, sess = AR.ENTRY_SETS[int(r.es)]
    E = AR.entry_set(tf, entry, pb, conf, ar, sess); o = np.argsort(E["m1"], kind="stable"); E = {k: v[o] for k, v in E.items()}
    risk = E["atr"] * r.k * ((0.7 + 0.6 * E["volp"]) if r.adapt else 1.0)
    G = AR.GR[tf]; T = G if r.ttf == "same" else AR.GR[r.ttf]
    res = A.sim(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1,
                T.trend_up, T.trend_dn, r.r1, r.f1, r.lock, r.trail, bool(r.brk), r.gb_a, r.gb_g, G_.COST_RT, 60 * 24 * 15)
    take = A.greedy(E["m1"], res[:, 2].astype(np.int64))
    t = pd.DataFrame(dict(s=name[:9], t_in=idx[E["m1"][take]], t_out=idx[res[take, 2].astype(int)], R=res[take, 0], risk=risk[take],
                          usd=res[take, 0] * risk[take], atr4=AR.GR["4h"].atr1[E["m1"][take]], mfe=res[take, 1]))
    allt.append(t)
    t26 = t[t.t_in >= Y26]
    print(f"\n{name}  (0.01 lot = 1 oz)  2026 Jan-Jul")
    print(f"   trades {len(t26)}, wins {(t26.usd>0).mean()*100:.0f}%, stop-loss distance median ${t26.risk.median():.0f} (min ${t26.risk.min():.0f}, max ${t26.risk.max():.0f})")
    print(f"   result at 0.01 lot: ${t26.usd.sum():+.0f}  | biggest win ${t26.usd.max():+.0f}  biggest loss ${t26.usd.min():+.0f}")
    print(f"   4H ATR at entry median ${t26.atr4.median():.0f} -> trail 3xATR4H = ${3*t26.atr4.median():.0f} behind best price")
a = pd.concat(allt).sort_values("t_out")
for per, m in (("2026 Jan-Jul", a.t_in >= Y26), ("2023-03..2026-07 (all GC)", a.t_in == a.t_in)):
    x = a[m]; eq = x.usd.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    mo = x.groupby(x.t_out.dt.strftime("%Y-%m")).usd.sum()
    print(f"\nBOTH strategies, 0.01 lot each, {per}: total ${x.usd.sum():+.0f}, max drawdown ${dd:.0f}, worst month ${mo.min():+.0f}, best month ${mo.max():+.0f}, months+ {(mo>0).mean()*100:.0f}%")

a.to_csv("champion2_dollars.csv", index=False)
for s_, g in a.groupby("s"):
    for per, m in (("2026", g.t_in >= Y26), ("2023-26", g.t_in == g.t_in)):
        x = g[m].sort_values("t_out"); eq = x.usd.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
        mo = x.groupby(x.t_out.dt.strftime("%Y-%m")).usd.sum()
        print(f"XX {s_} {per}: total ${x.usd.sum():+.0f} maxDD ${dd:.0f} worst month ${mo.min():+.0f} months+ {(mo>0).mean()*100:.0f}% trades {len(x)}")
x = a[a.t_in >= Y26]
print("XX 2026 monthly both:", x.groupby(x.t_out.dt.strftime("%Y-%m")).usd.sum().round(0).to_dict())
r = a[a.s.str.startswith("ROB-RUN")]
print("XX RUN15 share of trades whose peak passed 3xATR4H:", round((r.mfe * r.risk > 3 * r.atr4).mean(), 2))
