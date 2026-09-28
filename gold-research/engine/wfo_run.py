"""Monthly R per configuration (one position per strategy), for walk-forward re-optimisation."""
import itertools, time, numpy as np, pandas as pd
from multiprocessing import Pool
import adv_run as AR, adv as A, gcdata as G_
MONTHS = pd.date_range("2024-08-01", "2026-08-01", freq="MS", tz="UTC")
m1_month = np.searchsorted(MONTHS.values, AR.m1.index.values, side="right") - 1

def job(args):
    es_i, (k, adapt) = args
    tf, entry, pb, conf, ar, sess = AR.ENTRY_SETS[es_i]
    E = AR.entry_set(tf, entry, pb, conf, ar, sess)
    if len(E["m1"]) < 30: return None
    o = np.argsort(E["m1"], kind="stable")
    for key in E: E[key] = E[key][o]
    risk = E["atr"] * k * ((0.7 + 0.6 * E["volp"]) if adapt else 1.0)
    G = AR.GR[tf]; mon = m1_month[E["m1"]]
    keys, MR, MN, MW = [], [], [], []
    for (r1, f1, lk), (ttf, m, brk, gb) in itertools.product(AR.TPS, AR.RUN):
        T = G if ttf == "same" else AR.GR[ttf]
        res = A.sim(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c,
                    T.mgmt, T.atr1, T.trend_up, T.trend_dn, r1, f1, lk, m, brk, gb[0], gb[1], G_.COST_RT, 60 * 24 * 15)
        take = A.greedy(E["m1"], res[:, 2].astype(np.int64))
        R = res[take, 0]; mm = mon[take]
        MR.append(np.bincount(mm, weights=R, minlength=24)[:24])
        MN.append(np.bincount(mm, minlength=24)[:24])
        MW.append(np.bincount(mm, weights=(R > 0).astype(float), minlength=24)[:24])
        keys.append((es_i, k, adapt, r1, f1, lk, ttf, m, brk, gb[0], gb[1]))
    return keys, np.array(MR, np.float32), np.array(MN, np.int16), np.array(MW, np.int16)

if __name__ == "__main__":
    t = time.time()
    jobs = [(i, s) for i in range(len(AR.ENTRY_SETS)) for s in AR.SLS]
    K, R, N, W = [], [], [], []
    with Pool(4) as p:
        for j, out in enumerate(p.imap_unordered(job, jobs, chunksize=1)):
            if out is None: continue
            K += out[0]; R.append(out[1]); N.append(out[2]); W.append(out[3])
            if j % 100 == 0: print(j, round(time.time() - t), flush=True)
    keys = pd.DataFrame(K, columns=["es","k","adapt","r1","f1","lock","ttf","trail","brk","gb_a","gb_g"])
    keys.to_parquet("wfo_keys.parquet")
    np.savez_compressed("wfo_monthly.npz", R=np.vstack(R), N=np.vstack(N), W=np.vstack(W))
    print("done", len(keys), round(time.time() - t))
