"""Self-calibrating trade management: every 'constant' is measured from the recent market, per trade.

For each signal k (all arrays are per-trade):
  risk_k   : stop distance (price)            <- quantile of recent signals' adverse excursions
  r1_k     : TP1 in R                         <- quantile of recent signals' favourable excursions
  trail_k  : chandelier width (price)         <- quantile of recent in-trend pullback depths on the runner TF
Management otherwise as adv.sim (TP1 partial + lock, runner trail on runner-TF closes, trend-break exit).
"""
import numpy as np
from numba import njit


@njit(cache=True)
def excursions(ent, dirs, lvl, h, l, horizon):
    """Market measurement for each signal: max adverse / favourable move over the next `horizon` 1m bars."""
    K = len(ent); n = len(h)
    mae = np.zeros(K); mfe = np.zeros(K); end = np.zeros(K, np.int64)
    for k in range(K):
        i0 = ent[k] + 1; i1 = min(n, i0 + horizon)
        a = 0.0; f = 0.0
        for i in range(i0, i1):
            if dirs[k] == 1:
                a = max(a, lvl[k] - l[i]); f = max(f, h[i] - lvl[k])
            else:
                a = max(a, h[i] - lvl[k]); f = max(f, lvl[k] - l[i])
        mae[k] = a; mfe[k] = f; end[k] = i1
    return mae, mfe, end


@njit(cache=True)
def rolling_quantile_known(ent, end, x, lookback, q, default):
    """For signal k: q-quantile of x over the last `lookback` signals whose measurement window ended before ent[k]."""
    K = len(ent); out = np.full(K, default)
    buf = np.empty(lookback)
    for k in range(K):
        c = 0
        j = k - 1
        while j >= 0 and c < lookback:
            if end[j] <= ent[k]:
                buf[c] = x[j]; c += 1
            j -= 1
        if c >= max(10, lookback // 3):
            out[k] = np.quantile(buf[:c], q)
    return out


@njit(cache=True)
def sim_dyn(ent, dirs, lvl, risk_arr, r1_arr, trail_arr, o, h, l, c, mgmt_t, tu_t, td_t,
            f1, lock, brk, cost, max_bars):
    n = len(o); K = len(ent)
    out = np.zeros((K, 4))
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
                            tp_done = True; out[k, 3] = 1.0
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


@njit(cache=True)
def trend_pullback_depths(close, high, low, atr, bull, bear):
    """On a bar series: for every trend episode (stack aligned), the deepest pullback from the running extreme,
    in ATR units. Returns per-bar arrays: depth of the episode that ENDED on this bar (else nan)."""
    n = len(close); out = np.full(n, np.nan)
    state = 0; ext = 0.0; deep = 0.0
    for i in range(n):
        s = 1 if bull[i] else (-1 if bear[i] else 0)
        if s != state:
            if state != 0 and atr[i] > 0:
                out[i] = deep
            state = s; deep = 0.0
            ext = high[i] if s == 1 else low[i]
        elif state == 1:
            ext = max(ext, high[i]); d = (ext - low[i]) / atr[i] if atr[i] > 0 else 0.0; deep = max(deep, d)
        elif state == -1:
            ext = min(ext, low[i]); d = (high[i] - ext) / atr[i] if atr[i] > 0 else 0.0; deep = max(deep, d)
    return out
