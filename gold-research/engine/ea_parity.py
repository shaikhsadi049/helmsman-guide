"""EA-style variant of the dynamic portfolio: MT5 ATR (SMA of true range) and excursions measured on signal-TF bars."""
import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import dyn_run as DR, adv3 as D, adv as A, gcdata as G_, adv_run as AR
idx = AR.m1.index; S25 = DR.S25
picks = pickle.load(open("dyn_picks.pkl", "rb"))
def sma_atr(bars, n=14):
    pc = bars.close.shift(1)
    tr = pd.concat([bars.high - bars.low, (bars.high - pc).abs(), (bars.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().bfill().values
ATR_SMA = {tf: sma_atr(AR.GR[tf].bars) for tf in ("5min", "15min", "1h", "4h")}
def tf_excursions(G, bars_i, dirs, lvl, hor_min):
    b = G.bars; hb = max(1, hor_min // int(pd.Timedelta(G.tf).total_seconds() // 60))
    H, L = b.high.values, b.low.values; mae = np.zeros(len(bars_i)); mfe = np.zeros(len(bars_i)); end = np.zeros(len(bars_i), np.int64)
    for k, (bi, d, lv) in enumerate(zip(bars_i, dirs, lvl)):
        s = slice(bi + 1, min(len(H), bi + 1 + hb))
        mae[k] = (lv - L[s].min()) if d == 1 else (H[s].max() - lv); mfe[k] = (H[s].max() - lv) if d == 1 else (lv - L[s].min())
        end[k] = G.pos[min(len(H) - 1, bi + hb)]
    return np.maximum(mae, 0), np.maximum(mfe, 0), end
rows = []
for variant in ("research (RMA ATR, 1m excursions)", "EA-style (SMA ATR, TF-bar excursions)"):
    T = []
    for r in picks:
        tf, E = DR.prep(int(r.es)); G = AR.GR[tf]
        if variant.startswith("EA"):
            E["atr"] = ATR_SMA[tf][E["bar"]]
            mae, mfe, end = tf_excursions(G, E["bar"], E["dir"], E["lvl"], DR.HOR[tf])
            E["mae_a"], E["mfe_a"], E["end"] = mae / E["atr"], mfe / E["atr"], end
            E["atr4"] = ATR_SMA["4h"][AR.GR["4h"].idx[E["m1"]]]
        k_t = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mae_a"], int(r.lb), r.qsl, 2.0), 0.5, 8.0)
        risk = k_t * E["atr"]
        r1 = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mfe_a"], int(r.lb), r.qtp, 1.0) / k_t, 0.2, 3.0)
        tw = DR.trail_quantile(E["m1"], r.qtr) * E["atr4"]
        res = D.sim_dyn(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c,
                        DR.G4.mgmt, DR.G4.trend_up, DR.G4.trend_dn, 0.5, r.lock, bool(r.brk), G_.COST_RT, 60 * 24 * 30)
        live = np.where(idx[E["m1"]] >= S25)[0]; take = A.greedy(E["m1"][live], res[live, 2].astype(np.int64)); s = live[take]
        T.append(pd.DataFrame(dict(tf=tf, R=res[s, 0], q=idx[E["m1"][s]].to_period("Q").astype(str))))
    T = pd.concat(T); w = T.R > 0; qs = T.groupby("q").R.sum()
    eq = T.R.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    print(f"{variant:40s} trades {len(T)} win {w.mean()*100:.0f}% PF {T.R[w].sum()/-T.R[~w].sum():.2f} totR {T.R.sum():+.1f} | quarters positive {(qs>0).sum()}/{len(qs)} | per TF: " +
          " ".join(f"{tf}:{g.R.sum():+.0f}R/{(g.R>0).mean()*100:.0f}%" for tf, g in T.groupby("tf")))
