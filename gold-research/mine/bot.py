"""MINE step 1: bar-outcome tables. For every closed bar of TF (5min/15min/1h) since 2024-06 and both directions,
the net R of 48 standard exits on the 1m path (entry = next 1m open after the bar closes; cost $0.34/oz).
Stops are ATR multiples (MT5-style SMA ATR14 of the TF) so any entry rule can be scored by lookup."""
import sys; sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, itertools, json, time, warnings; warnings.filterwarnings("ignore")
from numba import njit, prange
import dyn2_run as R2, gcdata as G_, v3_parity as V
o = R2.m1.open.values; h = R2.m1.high.values; l = R2.m1.low.values; c = R2.m1.close.values
H0 = pd.Timestamp("2024-06-01", tz="UTC")
EXITS = [dict(k=k, tp=tp, mg=mg) for k, tp, mg in itertools.product((1.0, 2.0, 3.0), (0, 1, 2, 3), ("plain", "be1", "ch3", "rat2"))]
@njit(cache=True)
def sim(i0, pos, risk, tp, mg, atr, hor, o, h, l, c, cost):
    n = len(o); i = i0 + 1
    if i >= n: return np.nan, i0, 0.0
    e = o[i]; stop = e - pos * risk; tpx = e + pos * tp * risk; best = e; mfe = 0.0; end = min(n, i + hor)
    while i < end:
        if (pos == 1 and o[i] <= stop) or (pos == -1 and o[i] >= stop): return ((o[i] - e) * pos - cost) / risk, i, mfe
        hf = (h[i] - o[i]) < (o[i] - l[i]); ff = (pos == 1 and hf) or (pos == -1 and not hf)
        fe = h[i] if pos == 1 else l[i]; ae = l[i] if pos == 1 else h[i]
        for ph in range(2):
            if (ph == 0) == ff:
                if tp > 0 and ((pos == 1 and fe >= tpx) or (pos == -1 and fe <= tpx)):
                    px = o[i] if ((pos == 1 and o[i] >= tpx) or (pos == -1 and o[i] <= tpx)) else tpx
                    return ((px - e) * pos - cost) / risk, i, mfe
                f = (fe - e) * pos / risk
                if f > mfe: mfe = f
            else:
                if (pos == 1 and ae <= stop) or (pos == -1 and ae >= stop): return ((stop - e) * pos - cost) / risk, i, mfe
        best = max(best, h[i]) if pos == 1 else min(best, l[i]); prof = (best - e) * pos
        if mg == 1 and prof >= risk:
            ns = e + pos * 0.05 * risk
            if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        elif mg == 2:
            ns = best - pos * 3.0 * atr
            if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        elif mg == 3 and prof >= 2 * risk:
            ns = e + pos * 0.5 * prof
            if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        i += 1
    j = min(i, n - 1); return ((c[j] - e) * pos - cost) / risk, j, mfe
@njit(parallel=True, cache=True)
def sim_all(m, atr, k, tp, mg, hor, o, h, l, c, cost):
    K = len(m); R = np.empty((K, 2), np.float32); X = np.empty((K, 2), np.int32)
    for q in prange(K):
        for d in range(2):
            pos = 1 if d == 0 else -1
            r, x, _ = sim(m[q], pos, k * atr[q], tp, mg, atr[q], hor, o, h, l, c, cost)
            R[q, d] = r; X[q, d] = x
    return R, X
HOR = {"5min": 1440, "15min": 2880, "1h": 7200}
MG = {"plain": 0, "be1": 1, "ch3": 2, "rat2": 3}
for tf in ("5min", "15min", "1h"):
    G = R2.GR[tf]; atr = V.sma_atr(G.bars)
    sel = (G.bars.index >= H0)
    m = G.pos[sel].astype(np.int64); a = atr[sel]
    t0 = time.time()
    Rall = np.empty((len(m), 2, len(EXITS)), np.float32); Xall = np.empty((len(m), 2, len(EXITS)), np.int32)
    for j, ex in enumerate(EXITS):
        R, X = sim_all(m, a, ex["k"], ex["tp"], MG[ex["mg"]], HOR[tf], o, h, l, c, G_.COST_RT)
        Rall[:, :, j] = R; Xall[:, :, j] = X
    np.save(f"R_{tf}.npy", Rall); np.save(f"X_{tf}.npy", Xall)
    pd.DataFrame(dict(m1=m, atr=a, time=R2.idx[m]), index=G.bars.index[sel]).to_parquet(f"bars_{tf}.parquet")
    print(tf, len(m), "bars", round(time.time() - t0), "s", flush=True)
json.dump(EXITS, open("exits.json", "w"))
