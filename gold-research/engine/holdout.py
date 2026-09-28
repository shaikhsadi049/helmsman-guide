"""Blind test on never-used real GC data: 2023-03-01 .. 2024-07-31."""
import numpy as np, pandas as pd, warnings, sys
from multiprocessing import Pool
warnings.filterwarnings("ignore")
import adv_run as AR, adv as A, gcdata as G_
H0, H1 = pd.Timestamp("2023-03-01", tz="UTC"), pd.Timestamp("2024-08-01", tz="UTC")
for G in AR.GR.values():
    G.trade_ok = (AR.m1.index >= H0) & (AR.m1.index < H1)
CACHE = {}
def entries(es):
    if es not in CACHE:
        tf, entry, pb, conf, ar, sess = AR.ENTRY_SETS[es]
        E = AR.entry_set(tf, entry, pb, conf, ar, sess)
        o = np.argsort(E["m1"], kind="stable")
        CACHE[es] = {k: v[o] for k, v in E.items()}
    return CACHE[es]
def run(r):
    tf = AR.ENTRY_SETS[int(r.es)][0]; E = entries(int(r.es))
    if len(E["m1"]) < 5: return None
    risk = E["atr"] * r.k * ((0.7 + 0.6 * E["volp"]) if r.adapt else 1.0)
    G = AR.GR[tf]; T = G if r.ttf == "same" else AR.GR[r.ttf]
    res = A.sim(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1,
                T.trend_up, T.trend_dn, r.r1, r.f1, r.lock, r.trail, bool(r.brk), r.gb_a, r.gb_g, G_.COST_RT, 60 * 24 * 15)
    take = A.greedy(E["m1"], res[:, 2].astype(np.int64))
    return res[take, 0], AR.m1.index[E["m1"][take]]
def job(rows):
    out = []
    for _, r in rows.iterrows():
        x = run(r)
        if x is None: out.append((r.name, 0, np.nan, np.nan, 0, np.nan)); continue
        R = x[0]; w = R > 0; gl = -R[~w].sum()
        eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max() if len(R) else 0
        out.append((r.name, len(R), w.mean() * 100 if len(R) else np.nan, R[w].sum() / gl if gl > 0 else np.nan, R.sum(), dd))
    return out
if __name__ == "__main__":
    both = pd.read_parquet("both_years.parquet")
    allc = pd.read_parquet("adv_results.parquet")
    allc["tf"] = [AR.ENTRY_SETS[i][0] for i in allc.es]
    ONLY = __import__("os").environ.get("ONLY")
    sets = {
        "ELITE  pf>=1.5 & win>=60 both yrs": both[(both.pfmin >= 1.5) & (both.winmin >= 60)],
        "ELITE  pf>=2 both yrs": both[both.pfmin >= 2],
        "TOP50/TF by min(R/DD) both yrs": pd.concat([g.sort_values("rdd", ascending=False).head(50) for _, g in both.groupby("tf")]),
        "RANDOM 600 (any config)": allc.sample(600, random_state=0),
    }
    res = {}
    for name, s in sets.items():
        if ONLY and not name.startswith(ONLY): continue
        s = s.copy(); s.index = range(len(s))
        chunks = [s.iloc[i::4] for i in range(4)]
        with Pool(4) as p:
            rows = [x for c in p.map(job, chunks) for x in c]
        h = pd.DataFrame(rows, columns=["i", "n", "win", "pf", "R", "dd"]).set_index("i").sort_index()
        h.columns = [c + "_h" for c in h.columns]; s = s.join(h); res[name] = s
        print(f"\n### {name}: {len(s)} configs  -> BLIND 2023-03..2024-07")
        for tf, g in s.groupby("tf"):
            print(f"   {tf:6s} n={len(g):4d} | profitable {(g.R_h>0).mean()*100:3.0f}% | median PF {g.pf_h.median():.2f} | median win {g.win_h.median():.0f}% | median R {g.R_h.median():+.1f} | median DD {g.dd_h.median():.1f} | median trades {g.n_h.median():.0f}")
        s.to_parquet("holdout_" + "".join(ch for ch in name if ch.isalnum()) + ".parquet")
