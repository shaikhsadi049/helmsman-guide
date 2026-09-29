"""Aggressive variants of the dynamic portfolio, with %-risk compounding and Monte Carlo ruin odds."""
import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import dyn_run as DR, adv3 as D, adv4, gcdata as G_, adv_run as AR
idx = AR.m1.index; S25 = DR.S25
picks = pickle.load(open("dyn_picks.pkl", "rb"))
PREP = {int(r.es): DR.prep(int(r.es)) for r in picks}
def trades(f1, pyramid):
    T = []
    for r in picks:
        tf, E = PREP[int(r.es)]; G = AR.GR[tf]
        k = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mae_a"], int(r.lb), r.qsl, 2.0), 0.5, 8.0); risk = k * E["atr"]
        r1 = np.clip(D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mfe_a"], int(r.lb), r.qtp, 1.0) / k, 0.2, 3.0)
        tw = DR.trail_quantile(E["m1"], r.qtr) * E["atr4"]
        res = adv4.sim_dyn2(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c,
                            DR.G4.mgmt, DR.G4.trend_up, DR.G4.trend_dn, f1, r.lock, bool(r.brk), G_.COST_RT, 60 * 24 * 30)
        live = np.where(idx[E["m1"]] >= S25)[0]
        open_ = []                      # (exit_idx, lock_idx, dir)
        keep = []
        for j in live:
            t = E["m1"][j]
            open_ = [p for p in open_ if p[0] >= t]
            if not open_:
                ok = True
            elif pyramid and len(open_) < pyramid:
                # add only if every open position already has its stop locked in profit, same direction
                ok = all(p[1] >= 0 and p[1] <= t and p[2] == E["dir"][j] for p in open_)
            else:
                ok = False
            if ok:
                keep.append(j); open_.append((int(res[j, 2]), int(res[j, 4]), E["dir"][j]))
        s = np.array(keep, int)
        T.append(pd.DataFrame(dict(t_in=idx[E["m1"][s]], t_out=idx[res[s, 2].astype(int)], R=res[s, 0])))
    return pd.concat(T).sort_values("t_out")
rng = np.random.default_rng(3)
print("variant                                 | trades win   PF    totR | risk | 19-month path: return  maxDD | MC 12m: median  5th pct  P(DD>30%) P(DD>50%)")
for name, f1, pyr in (("A base (half at TP1)", 0.5, 0), ("B lock-only TP1", 1e-9, 0), ("C base + pyramid<=3", 0.5, 3), ("D lock-only + pyramid<=3", 1e-9, 3)):
    T = trades(f1, pyr); R = T.R.values; w = R > 0
    head = f"{name:40s}| {len(R):5d} {w.mean()*100:3.0f}% {R[w].sum()/-R[~w].sum():5.2f} {R.sum():+7.1f}"
    for rp in (1.0, 2.0, 3.0):
        eq = np.cumprod(1 + R * rp / 100); dd = (1 - eq / np.maximum.accumulate(eq)).max()
        n = int(len(R) / 19 * 12); fin = []; dds = []
        for _ in range(4000):
            e = np.cumprod(1 + np.maximum(rng.choice(R, n) * rp / 100, -0.99)); fin.append(e[-1] - 1); dds.append((1 - e / np.maximum.accumulate(e)).max())
        fin, dds = np.array(fin), np.array(dds)
        print(f"{head} | {rp:3.0f}% | {(eq[-1]-1)*100:+9.0f}% {dd*100:5.1f}% | {np.median(fin)*100:+8.0f}% {np.percentile(fin,5)*100:+7.0f}% {np.mean(dds>0.3)*100:6.1f}% {np.mean(dds>0.5)*100:6.1f}%")
        head = " " * len(head)
