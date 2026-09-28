"""Self-calibrating DTC: stops/targets/trails measured from the market at each signal. Judged on 2025-01..2026-07 by quarter."""
import itertools, time, numpy as np, pandas as pd, warnings
from multiprocessing import Pool
warnings.filterwarnings("ignore")
import adv_run as AR, adv as A, adv3 as D, gcdata as G_
m1 = AR.m1; idx = m1.index
S25 = pd.Timestamp("2025-01-01", tz="UTC")
Q = np.array(idx.to_period("Q").astype(str))
HOR = {"5min": 1440, "15min": 1440, "1h": 4320}
# 4H trend-episode pullback depths (market-measured runner giveback)
G4 = AR.GR["4h"]; b4 = G4.bars
dep = D.trend_pullback_depths(b4.close.values, b4.high.values, b4.low.values, G4.F.atr, G4.F.bull, G4.F.bear)
ep_end_m1 = G4.pos[~np.isnan(dep)]; ep_depth = dep[~np.isnan(dep)]
def trail_quantile(sig_m1, q, n=20):
    cnt = np.searchsorted(ep_end_m1, sig_m1, side="right")
    return np.array([np.quantile(ep_depth[max(0, c - n):c], q) if c >= 8 else 3.0 for c in cnt])
def prep(es):
    tf, entry, pb, conf, ar, sess = AR.ENTRY_SETS[es]
    for G in AR.GR.values(): G.trade_ok = idx >= pd.Timestamp("2024-06-01", tz="UTC")   # history for calibration
    E = AR.entry_set(tf, entry, pb, conf, ar, sess); o = np.argsort(E["m1"], kind="stable"); E = {k: v[o] for k, v in E.items()}
    G = AR.GR[tf]
    mae, mfe, end = D.excursions(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], G.h, G.l, HOR[tf])
    E["mae_a"] = mae / E["atr"]; E["mfe_a"] = mfe / E["atr"]; E["end"] = end
    E["atr4"] = G4.atr1[E["m1"]]
    return tf, E
def job(es):
    tf, E = prep(es)
    if len(E["m1"]) < 80: return []
    G = AR.GR[tf]; live = idx[E["m1"]] >= S25
    rows = []
    for lb in (30, 60):
        for qsl in (0.5, 0.7, 0.85):
            k_t = D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mae_a"], lb, qsl, 2.0)
            k_t = np.clip(k_t, 0.5, 8.0); risk = k_t * E["atr"]
            for qtp in (0.0, 0.3, 0.5):
                if qtp > 0:
                    tp_a = D.rolling_quantile_known(E["m1"].astype(np.int64), E["end"], E["mfe_a"], lb, qtp, 1.0)
                    r1 = np.clip(tp_a / k_t, 0.2, 3.0)
                else:
                    r1 = np.zeros(len(risk))
                for lock in ((0.0, 0.25) if qtp > 0 else (0.0,)):
                    for qtr in (0.0, 0.5, 0.8, 1.0):
                        tw = trail_quantile(E["m1"], qtr) * E["atr4"] if qtr > 0 else np.zeros(len(risk))
                        for brk in (True, False):
                            if qtr == 0 and not brk: continue
                            res = D.sim_dyn(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c,
                                            G4.mgmt, G4.trend_up, G4.trend_dn, 0.5, lock, brk, G_.COST_RT, 60 * 24 * 30)
                            sel = np.where(live)[0]
                            take = A.greedy(E["m1"][sel], res[sel, 2].astype(np.int64))
                            R = res[sel[take], 0]; qq = Q[E["m1"][sel[take]]]
                            if len(R) < 30: continue
                            qs = pd.Series(R).groupby(qq).sum()
                            w = R > 0; eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
                            rows.append(dict(es=es, tf=tf, lb=lb, qsl=qsl, qtp=qtp, lock=lock, qtr=qtr, brk=brk, n=len(R), win=w.mean() * 100,
                                             pf=R[w].sum() / -R[~w].sum() if (~w).any() else 99, R=R.sum(), dd=dd, qmin=qs.min(), qpos=(qs > 0).mean() * 100,
                                             k_med=np.median(k_t[live]), r1_med=np.median(r1[live]) if qtp > 0 else 0,
                                             tr_med=np.median((tw / E["atr4"])[live]) if qtr > 0 else 0))
    return rows
if __name__ == "__main__":
    t = time.time()
    with Pool(4) as p:
        rows = [r for rr in p.imap_unordered(job, range(len(AR.ENTRY_SETS))) for r in rr]
    df = pd.DataFrame(rows); df.to_parquet("dyn_results.parquet")
    print("configs", len(df), "time", round(time.time() - t))
