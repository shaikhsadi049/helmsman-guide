"""Advanced, EA-style trade management simulated on the 1m path.

Per trade:
  - initial stop  = k * ATR(entry TF)  (optionally volatility-adaptive)
  - TP1           : close fraction f at r1 R, then lock stop at +lock R (instant, like an EA)
  - runner        : chandelier trail m * ATR(trail TF) updated on trail-TF closes
                    + optional exit when the trail-TF EMA stack breaks
                    + optional profit-lock: once MFE >= a R, never give back more than g of the peak
Returns per trade [R, MFE_R, exit_index, win_flag_of_TP1].
"""
import numpy as np
from numba import njit


@njit(cache=True)
def sim(ent, dirs, lvl, risk_arr, o, h, l, c,
        mgmt_t, atr_t, tu_t, td_t,
        r1, f1, lock, trail_m, brk, gb_a, gb_g, cost, max_bars):
    n = len(o)
    K = len(ent)
    out = np.zeros((K, 4))
    for k in range(K):
        i = ent[k] + 1
        if i >= n:
            out[k, 0] = np.nan
            continue
        pos = dirs[k]
        risk = risk_arr[k]
        entry = o[i]
        stop = lvl[k] - pos * risk
        tp1 = lvl[k] + pos * r1 * risk
        size1 = f1 if r1 > 0 else 0.0
        run = 1.0 - size1
        pnl = 0.0
        mfe = 0.0
        best = entry
        tp_done = size1 == 0.0
        pend = False
        end = min(n, i + max_bars)
        closed = False
        while i < end:
            if pend:
                left = run + (0.0 if tp_done else size1)
                pnl += (o[i] - entry) * pos * left - cost * left
                closed = True
                break
            # gap through stop
            if (pos == 1 and o[i] <= stop) or (pos == -1 and o[i] >= stop):
                left = run + (0.0 if tp_done else size1)
                pnl += (o[i] - entry) * pos * left - cost * left
                closed = True
                break
            high_first = (h[i] - o[i]) < (o[i] - l[i])
            fav_first = (pos == 1 and high_first) or (pos == -1 and not high_first)
            fav_ext = h[i] if pos == 1 else l[i]
            adv_ext = l[i] if pos == 1 else h[i]
            for ph in range(2):
                if (ph == 0) == fav_first:
                    if not tp_done:
                        hit = (fav_ext >= tp1) if pos == 1 else (fav_ext <= tp1)
                        if hit:
                            gap = (o[i] >= tp1) if pos == 1 else (o[i] <= tp1)
                            px = o[i] if gap else tp1
                            pnl += (px - entry) * pos * size1 - cost * size1
                            tp_done = True
                            out[k, 3] = 1.0
                            ls = entry + pos * lock * risk
                            if (pos == 1 and ls > stop) or (pos == -1 and ls < stop):
                                stop = ls
                    fav = (fav_ext - entry) * pos / risk
                    if fav > mfe:
                        mfe = fav
                else:
                    hit = (adv_ext <= stop) if pos == 1 else (adv_ext >= stop)
                    if hit:
                        left = run + (0.0 if tp_done else size1)
                        pnl += (stop - entry) * pos * left - cost * left
                        closed = True
                        break
            if closed:
                break
            if run <= 1e-9 and tp_done:
                closed = True
                break
            best = max(best, h[i]) if pos == 1 else min(best, l[i])
            # profit lock (checked every minute, like an EA on ticks)
            if gb_a > 0 and mfe >= gb_a:
                ls = entry + pos * (1.0 - gb_g) * mfe * risk
                if (pos == 1 and ls > stop) or (pos == -1 and ls < stop):
                    stop = ls
            if mgmt_t[i]:
                if trail_m > 0:
                    ns = best - pos * trail_m * atr_t[i]
                    if (pos == 1 and ns > stop) or (pos == -1 and ns < stop):
                        stop = ns
                if brk and ((pos == 1 and not tu_t[i]) or (pos == -1 and not td_t[i])):
                    pend = True
            i += 1
        if not closed:
            left = run + (0.0 if tp_done else size1)
            last = c[min(i, n - 1)]
            pnl += (last - entry) * pos * left - cost * left
        out[k, 0] = pnl / risk
        out[k, 1] = mfe
        out[k, 2] = min(i, n - 1)
    return out


@njit(cache=True)
def greedy(entry_idx, exit_idx):
    """One position at a time: take a signal only if the previous trade is already closed."""
    K = len(entry_idx)
    take = np.zeros(K, np.bool_)
    free_at = -1
    for k in range(K):
        if entry_idx[k] > free_at:
            take[k] = True
            free_at = exit_idx[k]
    return take
