import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import dyn_run as DR, adv3 as D, adv as A, gcdata as G_, adv_run as AR
ES = AR.ENTRY_SETS; idx = AR.m1.index; S25 = DR.S25
top = pd.read_parquet("dyn_top.parquet")
# one pick per timeframe: best all-quarters-positive config by R/DD (different entry sets)
picks = [g.iloc[0] for _, g in top.groupby("tf")]
def trades(r):
    tf, E = DR.prep(int(r.es)); G = AR.GR[tf]
    k_t = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mae_a"], int(r.lb), r.qsl, 2.0), 0.5, 8.0)
    risk = k_t * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mfe_a"], int(r.lb), r.qtp, 1.0) / k_t, 0.2, 3.0) if r.qtp > 0 else np.zeros(len(risk))
    tw = DR.trail_quantile(E["m1"], r.qtr) * E["atr4"] if r.qtr > 0 else np.zeros(len(risk))
    res = D.sim_dyn(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c,
                    DR.G4.mgmt, DR.G4.trend_up, DR.G4.trend_dn, 0.5, r.lock, bool(r.brk), G_.COST_RT, 60 * 24 * 30)
    live = np.where(idx[E["m1"]] >= S25)[0]
    take = A.greedy(E["m1"][live], res[live, 2].astype(np.int64)); s = live[take]
    return pd.DataFrame(dict(tf=tf, t_in=idx[E["m1"][s]], t_out=idx[res[s, 2].astype(int)], R=res[s, 0], risk=risk[s], usd=res[s, 0] * risk[s],
                             sl_usd=risk[s], tp1_usd=r1[s] * risk[s], trail_usd=tw[s]))
T = pd.concat([trades(r) for r in picks]).sort_values("t_out")
for r in picks:
    e = ES[int(r.es)]; x = T[T.tf == r.tf]
    print(f"{r.tf:5s} {e[1]}{e[2] if e[1]=='pullback' else ''} conf={'+'.join(e[3]) or '-'} adx={e[4]} sess={e[5]} | lookback {r.lb} SLq {r.qsl} TPq {r.qtp} lock {r.lock} trailq {r.qtr} brk {r.brk}")
    print(f"      trades {len(x)} win {(x.R>0).mean()*100:.0f}% totR {x.R.sum():+.1f} | 0.01 lot: total ${x.usd.sum():+.0f}, SL median ${x.sl_usd.median():.0f} (${x.sl_usd.min():.0f}-{x.sl_usd.max():.0f}), TP1 median ${x.tp1_usd.median():.0f}, trail median ${x.trail_usd.median():.0f}")
for per, m in (("2025-01..2026-07", T.t_in >= S25), ("2026 Jan-Jul", T.t_in >= pd.Timestamp("2026-01-01", tz="UTC"))):
    x = T[m]; eq = x.usd.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max(); eqR = x.R.cumsum(); ddR = (eqR.cummax().clip(lower=0) - eqR).max()
    mo = x.groupby(x.t_out.dt.strftime("%Y-%m")).usd.sum()
    print(f"\nPORTFOLIO {per}: trades {len(x)} win {(x.R>0).mean()*100:.0f}% PF {x.R[x.R>0].sum()/-x.R[x.R<=0].sum():.2f} totR {x.R.sum():+.1f} DD {ddR:.1f}R | 0.01 lot each: ${x.usd.sum():+.0f}, max DD ${dd:.0f}, months+ {(mo>0).mean()*100:.0f}%, worst month ${mo.min():+.0f}")
    print("   monthly $:", " ".join(f"{k[2:]}:{v:+.0f}" for k, v in mo.items()))
T.to_csv("dyn_portfolio_trades.csv", index=False)
pickle.dump(picks, open("dyn_picks.pkl", "wb"))
