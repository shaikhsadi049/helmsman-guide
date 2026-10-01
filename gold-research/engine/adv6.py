"""sim_dyn2 + profit ratchet: once open profit >= rat_a[k] R, stop >= entry + rat_f x open profit (every 1m bar)."""
import numpy as np
from numba import njit


@njit(cache=True)
def sim_rat(ent, dirs, lvl, risk_arr, r1_arr, trail_arr, rat_a, rat_f, o, h, l, c, mgmt_t, tu_t, td_t,
            f1, lock, brk, cost, max_bars):
    n = len(o); K = len(ent)
    out = np.zeros((K, 5)); out[:, 4] = -1
    for k in range(K):
        i = ent[k] + 1
        if i >= n:
            out[k, 0] = np.nan; continue
        pos = dirs[k]; risk = risk_arr[k]; r1 = r1_arr[k]; trail_w = trail_arr[k]
        entry = o[i]; stop = lvl[k] - pos * risk; tp1 = lvl[k] + pos * r1 * risk
        size1 = f1 if r1 > 0 else 0.0
        run = 1.0 - size1
        pnl = 0.0; mfe = 0.0; best = entry; tp_done = size1 == 0.0; pend = False; closed = False
        end = min(n, i + max_bars)
        while i < end:
            if pend:
                left = run + (0.0 if tp_done else size1)
                pnl += (o[i] - entry) * pos * left - cost * left; closed = True; break
            if (pos == 1 and o[i] <= stop) or (pos == -1 and o[i] >= stop):
                left = run + (0.0 if tp_done else size1)
                pnl += (o[i] - entry) * pos * left - cost * left; closed = True; break
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
                            tp_done = True; out[k, 3] = 1.0; out[k, 4] = i
                            ls = entry + pos * lock * risk
                            if (pos == 1 and ls > stop) or (pos == -1 and ls < stop): stop = ls
                    fav = (fav_ext - entry) * pos / risk
                    if fav > mfe: mfe = fav
                else:
                    hit = (adv_ext <= stop) if pos == 1 else (adv_ext >= stop)
                    if hit:
                        left = run + (0.0 if tp_done else size1)
                        pnl += (stop - entry) * pos * left - cost * left; closed = True; break
            if closed: break
            if run <= 1e-9 and tp_done:
                closed = True; break
            best = max(best, h[i]) if pos == 1 else min(best, l[i])
            if rat_a[k] > 0 and (best - entry) * pos >= rat_a[k] * risk:
                ns = entry + pos * rat_f * (best - entry)
                if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
            if mgmt_t[i]:
                if trail_w > 0:
                    ns = best - pos * trail_w
                    if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
                if brk and ((pos == 1 and not tu_t[i]) or (pos == -1 and not td_t[i])): pend = True
            i += 1
        if not closed:
            left = run + (0.0 if tp_done else size1)
            pnl += (c[min(i, n - 1)] - entry) * pos * left - cost * left
        out[k, 0] = pnl / risk; out[k, 1] = mfe; out[k, 2] = min(i, n - 1)
    return out


