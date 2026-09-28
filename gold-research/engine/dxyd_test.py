"""Daily DXY vs runners, judged over the whole 2025-01..2026-07 period (quarter by quarter)."""
import numpy as np, pandas as pd, pickle, warnings
from multiprocessing import Pool
warnings.filterwarnings("ignore")
import adv_run as AR, adv as A, gcdata as G_, engine as E
m1 = AR.m1; idx = m1.index
S25 = pd.Timestamp("2025-01-01", tz="UTC")
for G in AR.GR.values(): G.trade_ok = idx >= S25
dxy = pd.read_csv("/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/data/usd/dxy_daily.csv", parse_dates=["Date"]).set_index("Date").dxy
up = (E.ema(dxy, 20) > E.ema(dxy, 50)).astype(float)
# value of day d is known after that day -> usable from the next UTC day
up.index = (up.index + pd.Timedelta(days=1)).tz_localize("UTC")
usd_up = up.reindex(idx.normalize(), method="ffill").values == 1
usd_dn = ~usd_up
Q = idx.to_period("Q").astype(str)
K = pd.read_parquet("y2025_scores.parquet")
ES = pickle.load(open("adv_entry_sets.pkl", "rb"))
# universe: runner configs (brk=True) -- top 150 per timeframe by FULL 2025-01..2026-07 R/DD (no split)
K["Rall"] = K.R25 + K.R26
K["ddall"] = np.maximum(K.dd25, K.dd26)
K["sc"] = K.Rall / K.ddall.clip(lower=3)
U = pd.concat([g[(g.brk) & (g.n25 + g.n26 >= 40)].sort_values("sc", ascending=False).head(150) for _, g in K.groupby("tf")])
def run(r, mode):
    tf, entry, pb, conf, ar, sess = ES[int(r.es)]
    Ent = AR.entry_set(tf, entry, pb, conf, ar, sess); o = np.argsort(Ent["m1"], kind="stable"); Ent = {k: v[o] for k, v in Ent.items()}
    if mode == "entry_filter":
        keep = np.where(Ent["dir"] == 1, usd_dn[Ent["m1"]], usd_up[Ent["m1"]]); Ent = {k: v[keep] for k, v in Ent.items()}
    risk = Ent["atr"] * r.k * ((0.7 + 0.6 * Ent["volp"]) if r.adapt else 1.0)
    G = AR.GR[tf]; T = G if r.ttf == "same" else AR.GR[r.ttf]
    tu, td = T.trend_up, T.trend_dn
    if mode == "runner_exit_usd":      # exit when gold stack breaks OR USD daily turns against the trade
        tu = tu & usd_dn; td = td & usd_up
    if mode == "runner_extend_usd":    # keep runner while gold stack holds OR USD daily still supports
        tu = tu | usd_dn; td = td | usd_up
    res = A.sim(Ent["m1"].astype(np.int64), Ent["dir"].astype(np.int64), Ent["lvl"], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1,
                tu, td, r.r1, r.f1, r.lock, r.trail, bool(r.brk), r.gb_a, r.gb_g, G_.COST_RT, 60 * 24 * 30)
    take = A.greedy(Ent["m1"], res[:, 2].astype(np.int64))
    return pd.Series(res[take, 0], index=Q[Ent["m1"][take]])
MODES = ["base", "entry_filter", "runner_exit_usd", "runner_extend_usd"]
def job(r):
    out = {}
    for m in MODES:
        s = run(r, m); out[m] = (s.groupby(level=0).sum(), len(s), (s > 0).mean() * 100, s.sum())
    return r.tf, out
if __name__ == "__main__":
    with Pool(4) as p:
        res = p.map(job, [r for _, r in U.iterrows()])
    quarters = sorted({q for _, o in res for q in o["base"][0].index})
    for tf in ["5min", "15min", "1h"]:
        rr = [o for t, o in res if t == tf]
        print(f"\n===== {tf}: {len(rr)} runner configs, 2025-01..2026-07")
        for m in MODES:
            tot = np.array([o[m][3] for o in rr]); base = np.array([o["base"][3] for o in rr])
            qd = np.array([[o[m][0].get(q, 0) - o["base"][0].get(q, 0) for q in quarters] for o in rr])
            print(f"  {m:18s} median total R {np.median(tot):+6.1f} (vs base {np.median(base):+6.1f}) | median win {np.median([o[m][2] for o in rr]):3.0f}% | configs improved {np.mean(tot>base)*100:3.0f}%"
                  + ("" if m == "base" else " | median change per quarter: " + " ".join(f"{q[-2:]}{q[2:4]}:{np.median(qd[:, i]):+.1f}" for i, q in enumerate(quarters))))
