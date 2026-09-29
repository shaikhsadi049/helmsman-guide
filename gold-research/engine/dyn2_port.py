import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import dyn2_run as R2, adv3 as D, adv4, adv as A, gcdata as G_
idx = R2.idx
d = pd.read_parquet("dyn2_results.parquet"); d["rdd"] = d.R / d.dd.clip(lower=2)
cand = d[(d.qmin > 0) & (d.win >= 65)].sort_values("rdd", ascending=False).groupby(["fam", "tf"]).head(1)
def trades(r):
    tf, fam, nc, sess = R2.SETS[int(r.si)]; Ent = R2.entries(tf, fam, nc, sess); G = R2.GR[tf]
    m = Ent["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, Ent["end"], Ent["mae_a"], 60, r.qsl, 2.0), 0.5, 8.0); risk = k * Ent["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, Ent["end"], Ent["mfe_a"], 60, r.qtp, 1.0) / k, 0.1, 3.0)
    tw = R2.trail_q(m, r.qtr) * Ent["atr4"]
    res = adv4.sim_dyn2(m, Ent["dir"].astype(np.int64), Ent["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c, R2.G4.mgmt, R2.G4.trend_up, R2.G4.trend_dn,
                        r.f1 if r.f1 > 0 else 1e-9, r.lock, False, G_.COST_RT, 60 * 24 * 30)
    sel = np.where(idx[m] >= R2.S25)[0]; take = A.greedy(m[sel], res[sel, 2].astype(np.int64)); s = sel[take]
    return pd.DataFrame(dict(name=f"{tf} {fam} c{nc} {sess}", t_in=idx[m[s]], t_out=idx[res[s, 2].astype(int)], R=res[s, 0], dir=Ent["dir"][s]))
TR = {}
for _, r in cand.iterrows():
    t = trades(r); TR[t.name.iloc[0]] = t
def stats(names):
    T = pd.concat([TR[n] for n in names]).sort_values("t_out"); R = T.R.values; w = R > 0
    eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    q = T.groupby(T.t_in.dt.to_period("Q").astype(str)).R.sum(); mo = T.groupby(T.t_out.dt.strftime("%Y-%m")).R.sum()
    ev = pd.concat([pd.DataFrame({"t": T.t_in, "d": 1}), pd.DataFrame({"t": T.t_out, "d": -1})]).sort_values("t")
    return dict(n=len(R), win=w.mean() * 100, pf=R[w].sum() / -R[~w].sum(), R=R.sum(), dd=dd, rdd=R.sum() / max(dd, 2), qpos=(q > 0).sum(), nq=len(q),
                mpos=(mo > 0).mean() * 100, maxopen=ev.d.cumsum().max())
# greedy forward selection: add the strategy that most improves R/DD; stop when nothing improves it
chosen = []; best = 0
pool = list(TR)
while pool:
    scores = [(stats(chosen + [p])["rdd"], p) for p in pool]
    sc, p = max(scores)
    if sc <= best * 1.02 and chosen: break
    chosen.append(p); pool.remove(p); best = sc
    s = stats(chosen)
    print(f"+ {p:32s} -> trades {s['n']:4d} ({s['n']/19*12:.0f}/yr) win {s['win']:.0f}% PF {s['pf']:.2f} totR {s['R']:+.1f} DD {s['dd']:.1f}R R/DD {s['rdd']:.1f} quarters+ {s['qpos']}/{s['nq']} months+ {s['mpos']:.0f}% maxOpen {s['maxopen']}")
pickle.dump((chosen, cand), open("dyn2_portfolio.pkl", "wb"))
pd.concat([TR[n] for n in chosen]).to_csv("dyn2_portfolio_trades.csv", index=False)
print("\nALL", len(TR), "candidates together:", {k: round(v, 1) if isinstance(v, float) else v for k, v in stats(list(TR)).items()})
