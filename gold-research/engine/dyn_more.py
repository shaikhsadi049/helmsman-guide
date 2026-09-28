import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import dyn_run as DR, adv3 as D, adv as A, gcdata as G_, adv_run as AR
idx = AR.m1.index; S25 = DR.S25; ES = AR.ENTRY_SETS
top = pd.read_parquet("dyn_top.parquet")
PREP = {}
def trades(r, maxpos=1):
    es = int(r.es)
    if es not in PREP: PREP[es] = DR.prep(es)
    tf, E = PREP[es]; G = AR.GR[tf]
    k_t = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mae_a"], int(r.lb), r.qsl, 2.0), 0.5, 8.0); risk = k_t * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mfe_a"], int(r.lb), r.qtp, 1.0) / k_t, 0.2, 3.0) if r.qtp > 0 else np.zeros(len(risk))
    tw = DR.trail_quantile(E["m1"], r.qtr) * E["atr4"] if r.qtr > 0 else np.zeros(len(risk))
    res = D.sim_dyn(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c,
                    DR.G4.mgmt, DR.G4.trend_up, DR.G4.trend_dn, 0.5, r.lock, bool(r.brk), G_.COST_RT, 60 * 24 * 30)
    live = np.where(idx[E["m1"]] >= S25)[0]
    # allow up to `maxpos` simultaneous positions for this strategy
    ends = []; keep = []
    for j in live:
        ends = [e for e in ends if e >= E["m1"][j]]
        if len(ends) < maxpos:
            keep.append(j); ends.append(int(res[j, 2]))
    s = np.array(keep, int)
    return pd.DataFrame(dict(tf=tf, es=es, t_in=idx[E["m1"][s]], t_out=idx[res[s, 2].astype(int)], R=res[s, 0], usd=res[s, 0] * risk[s]))
def rep(T, label):
    T = T.sort_values("t_out"); R = T.R.values; w = R > 0
    eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    q = T.groupby(T.t_in.dt.to_period("Q").astype(str)).R.sum(); mo = T.groupby(T.t_out.dt.strftime("%Y-%m")).R.sum()
    ev = pd.concat([pd.DataFrame({"t": T.t_in, "d": 1}), pd.DataFrame({"t": T.t_out, "d": -1})]).sort_values("t")
    print(f"{label:48s} trades {len(T):4d} ({len(T)/19*12:.0f}/yr) win {w.mean()*100:3.0f}% PF {R[w].sum()/-R[~w].sum():.2f} totR {R.sum():+6.1f} DD {dd:5.1f}R | quarters+ {(q>0).sum()}/{len(q)} months+ {(mo>0).mean()*100:3.0f}% | max open {ev.d.cumsum().max()}")
base = [g.iloc[0] for _, g in top.groupby("tf")]
rep(pd.concat([trades(r) for r in base]), "A: 3 strategies (current EA)")
rep(pd.concat([trades(r, 2) for r in base]), "B: same 3, up to 2 positions each")
rep(pd.concat([trades(r, 3) for r in base]), "C: same 3, up to 3 positions each")
# D: add the best config from a DIFFERENT entry set per timeframe
extra = []
for tf, g in top.groupby("tf"):
    used = int(g.iloc[0].es); other = g[g.es != used]
    if len(other): extra.append(other.iloc[0])
for r in extra:
    e = ES[int(r.es)]; print(f"   extra {r.tf}: {e[1]}{e[2] if e[1]=='pullback' else ''} conf={'+'.join(e[3]) or '-'} adx={e[4]} sess={e[5]}")
rep(pd.concat([trades(r) for r in base + extra]), "D: 6 strategies (2 entry types per TF)")
rep(pd.concat([trades(r, 2) for r in base + extra]), "E: 6 strategies, up to 2 positions each")
