"""Tick-level check of the 4 fade slots: same signals and calibration; entry at the first print after the signal bar,
stop fills at the print that crosses it (real gap slippage), TP as a limit (touch, or strict trade-through), time exit."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from numba import njit
import mr as M, dyn2_run as R2, adv3 as D, adv as A, gcdata as G_, ticks as TK
idx = R2.idx
tk = TK.load_ticks("2024-12-15")
ts = tk.ts_event.values.astype("datetime64[ns]").astype(np.int64)
m1_ns = idx.values.astype("datetime64[ns]").astype(np.int64)
mi = np.clip(np.searchsorted(m1_ns, ts, side="right") - 1, 0, len(idx) - 1)
p = tk.price.values + G_.ADJ[mi]; del tk
print("ticks", len(p), flush=True)
@njit(cache=True)
def tick_fade(ent, endt, dirs, lvl, risk, r1, p, cost, strict):
    K = len(ent); out = np.zeros((K, 2))
    for k in range(K):
        i = ent[k] + 1
        if i >= len(p): out[k, 0] = np.nan; continue
        pos = dirs[k]; e = p[i]; sl = lvl[k] - pos * risk[k]; tp = lvl[k] + pos * r1[k] * risk[k]
        px = np.nan; j = i
        # entry print already beyond TP/SL
        while j < min(len(p), endt[k]):
            q = p[j]
            if (pos == 1 and q <= sl) or (pos == -1 and q >= sl): px = q; break
            hit = (q > tp) if (strict and pos == 1) else (q >= tp) if pos == 1 else ((q < tp) if strict else (q <= tp))
            if hit: px = tp if (pos == 1 and e < tp) or (pos == -1 and e > tp) else q; break
            j += 1
        if np.isnan(px): j = min(len(p), endt[k]) - 1; px = p[j]
        out[k, 0] = ((px - e) * pos - cost) / risk[k]; out[k, 1] = j
    return out
def rep(R, name):
    w = R > 0; return f"{name:14s} n {len(R)} win {w.mean()*100:3.0f}% PF {R[w].sum()/-R[~w].sum():.2f} sumR {R.sum():+6.1f}"
for spec in [("15min", "rsi2", "no4h", True), ("1h", "z2", "no4h", False), ("30min", "z2.5", "no4h", False), ("1h", "fbo", "no4h", True)]:
    tf = spec[0]; E = M.entries(*spec); m = E["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, .7, 2.0), 0.3, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, .5, 1.0) / k, 0.1, 5.0)
    live = np.where(idx[m] >= R2.S25)[0]
    bar_end = (idx[m[live]] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64)
    ent_t = np.searchsorted(ts, bar_end, side="left") - 1
    hor_ns = M.MRH[tf] * int(pd.Timedelta(tf).total_seconds()) * 10**9
    end_t = np.searchsorted(ts, bar_end + hor_ns, side="left")
    one = M.run(*spec, .7, .5)
    print(spec, "\n   " + rep(one.R.values, "1-minute"), flush=True)
    for strict in (False, True):
        res = tick_fade(ent_t.astype(np.int64), end_t.astype(np.int64), E["dir"][live].astype(np.int64), E["lvl"][live], risk[live], r1[live], p, G_.COST_RT, strict)
        take = A.greedy(ent_t, res[:, 1].astype(np.int64))
        print("   " + rep(res[take, 0], "tick strict" if strict else "tick touch"), flush=True)
