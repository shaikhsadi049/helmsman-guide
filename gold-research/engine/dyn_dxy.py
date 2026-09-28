"""Daily DXY applied to the dynamic runner: trail width scaled by whether the USD daily trend supports the gold trade."""
import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import dyn_run as DR, adv3 as D, adv as A, gcdata as G_, adv_run as AR, engine as E
idx = AR.m1.index; S25 = DR.S25
dxy = pd.read_csv("/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/data/usd/dxy_daily.csv", parse_dates=["Date"]).set_index("Date").dxy
up = (E.ema(dxy, 20) > E.ema(dxy, 50)).astype(float); up.index = (up.index + pd.Timedelta(days=1)).tz_localize("UTC")
usd_up = up.reindex(idx.normalize(), method="ffill").values == 1
top = pd.read_parquet("dyn_top.parquet")
# broad universe: top 60 all-quarters-positive dynamic configs per TF (not only the 3 picks)
U = pd.concat([g.head(60) for _, g in top.groupby("tf")])
PREP = {}
def run(r, sup_mult, against_mult):
    es = int(r.es)
    if es not in PREP: PREP[es] = DR.prep(es)
    tf, E0 = PREP[es]; Ent = dict(E0); G = AR.GR[tf]
    k_t = np.clip(D.rolling_quantile_known(Ent["m1"].astype(np.int64), Ent["end"], Ent["mae_a"], int(r.lb), r.qsl, 2.0), 0.5, 8.0)
    risk = k_t * Ent["atr"]
    r1 = np.clip(D.rolling_quantile_known(Ent["m1"].astype(np.int64), Ent["end"], Ent["mfe_a"], int(r.lb), r.qtp, 1.0) / k_t, 0.2, 3.0) if r.qtp > 0 else np.zeros(len(risk))
    tw = DR.trail_quantile(Ent["m1"], r.qtr) * Ent["atr4"] if r.qtr > 0 else np.zeros(len(risk))
    supports = np.where(Ent["dir"] == 1, ~usd_up[Ent["m1"]], usd_up[Ent["m1"]])     # USD falling helps gold longs
    tw = tw * np.where(supports, sup_mult, against_mult)
    res = D.sim_dyn(Ent["m1"].astype(np.int64), Ent["dir"].astype(np.int64), Ent["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c,
                    DR.G4.mgmt, DR.G4.trend_up, DR.G4.trend_dn, 0.5, r.lock, bool(r.brk), G_.COST_RT, 60 * 24 * 30)
    live = np.where(idx[Ent["m1"]] >= S25)[0]; take = A.greedy(Ent["m1"][live], res[live, 2].astype(np.int64)); s = live[take]
    R = res[s, 0]; q = pd.Series(R).groupby(idx[Ent["m1"][s]].to_period("Q").astype(str)).sum()
    return R.sum(), (R > 0).mean() * 100, (q > 0).mean() * 100
VARIANTS = [(1.0, 1.0), (1.5, 1.0), (2.0, 1.0), (1.0, 0.7), (1.5, 0.7), (1.3, 0.8)]
res = {v: [] for v in VARIANTS}
for _, r in U.iterrows():
    for v in VARIANTS: res[v].append((r.tf,) + run(r, *v))
base = pd.DataFrame(res[(1.0, 1.0)], columns=["tf", "R", "win", "qpos"])
for v in VARIANTS[1:]:
    x = pd.DataFrame(res[v], columns=["tf", "R", "win", "qpos"])
    out = []
    for tf in ["5min", "15min", "1h"]:
        m = x.tf == tf
        out.append(f"{tf}: median R {x.R[m].median():+.1f} (base {base.R[m].median():+.1f}), improved {np.mean(x.R[m].values > base.R[m].values)*100:.0f}%, all-quarters+ {np.mean(x.qpos[m]==100)*100:.0f}%")
    print(f"trail x{v[0]} when USD daily supports, x{v[1]} when against  ->  " + " | ".join(out))
