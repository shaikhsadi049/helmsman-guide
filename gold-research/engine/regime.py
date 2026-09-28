"""Regime study: every entry is simulated independently under many stop/exit settings on the 1m path,
so we can ask 'which stop / trail / runner giveback is best in THIS kind of market'."""
import numpy as np
import pandas as pd
from numba import njit
import gcdata as G_
import strat as S
import engine as E


@njit(cache=True)
def sim_many(ent, dirs, o, h, l, c, mgmt, trend_up, trend_dn, atr_arr, sl_dist, lvl,
             tp_r, tp_frac, be_leg, trail_atr, brk, cost, max_bars):
    """For each entry (signal at 1m index ent[k], fill next open) return [R, MFE_R, MAE_R, bars_held]."""
    n = len(o)
    K = len(ent)
    res = np.zeros((K, 4))
    nlegs = len(tp_r)
    rem = np.zeros(nlegs)
    for k in range(K):
        i0 = ent[k] + 1
        if i0 >= n:
            res[k, 0] = np.nan
            continue
        pos = dirs[k]
        risk = sl_dist[k]
        entry = o[i0]
        stop = lvl[k] - pos * risk
        tps = lvl[k] + pos * tp_r * risk
        for j in range(nlegs):
            rem[j] = tp_frac[j]
        pnl = 0.0
        best = entry
        legs = 0
        mfe = 0.0
        mae = 0.0
        pend_exit = False
        i = i0
        end = min(n, i0 + max_bars)
        while i < end:
            if pend_exit:
                left = rem.sum()
                pnl += (o[i] - entry) * pos * left - cost * left
                rem[:] = 0.0
                break
            fav = (h[i] - entry) * pos if pos == 1 else (entry - l[i])
            adv = (entry - l[i]) if pos == 1 else (h[i] - entry)
            if fav / risk > mfe:
                mfe = fav / risk
            if adv / risk > mae:
                mae = adv / risk
            if (pos == 1 and o[i] <= stop) or (pos == -1 and o[i] >= stop):
                left = rem.sum(); pnl += (o[i] - entry) * pos * left - cost * left; rem[:] = 0.0
                break
            high_first = (h[i] - o[i]) < (o[i] - l[i])
            fav_first = (pos == 1 and high_first) or (pos == -1 and not high_first)
            fav_ext = h[i] if pos == 1 else l[i]
            adv_ext = l[i] if pos == 1 else h[i]
            for ph in range(2):
                if (ph == 0) == fav_first:
                    for j in range(nlegs):
                        if rem[j] > 0 and tp_r[j] < 900:
                            hit = (fav_ext >= tps[j]) if pos == 1 else (fav_ext <= tps[j])
                            if hit:
                                gap = (o[i] >= tps[j]) if pos == 1 else (o[i] <= tps[j])
                                px = o[i] if gap else tps[j]
                                pnl += (px - entry) * pos * rem[j] - cost * rem[j]
                                rem[j] = 0.0; legs += 1
                else:
                    hit = (adv_ext <= stop) if pos == 1 else (adv_ext >= stop)
                    if hit:
                        left = rem.sum(); pnl += (stop - entry) * pos * left - cost * left; rem[:] = 0.0
                if rem.sum() <= 1e-9:
                    break
            if rem.sum() <= 1e-9:
                break
            if pos == 1:
                best = max(best, h[i])
            else:
                best = min(best, l[i])
            if mgmt[i]:
                if be_leg > 0 and legs >= be_leg:
                    if pos == 1 and stop < entry: stop = entry
                    if pos == -1 and stop > entry: stop = entry
                if trail_atr > 0:
                    ns = best - pos * trail_atr * atr_arr[i]
                    if (pos == 1 and ns > stop) or (pos == -1 and ns < stop):
                        stop = ns
                if brk and ((pos == 1 and not trend_up[i]) or (pos == -1 and not trend_dn[i])):
                    pend_exit = True
            i += 1
        if rem.sum() > 1e-9:          # time exit
            left = rem.sum(); last = c[min(i, n - 1)]
            pnl += (last - entry) * pos * left - cost * left
        res[k, 0] = pnl / risk
        res[k, 1] = mfe
        res[k, 2] = mae
        res[k, 3] = i - i0
    return res


def efficiency_ratio(close, n=20):
    ch = (close - close.shift(n)).abs()
    vol = close.diff().abs().rolling(n).sum()
    return (ch / vol).fillna(0)


def entries_and_features(G, entry="swing", htf=("4h", "1D"), sess=(7, 20), pb_ema=30):
    """Signals WITHOUT an ADX filter, so trend strength becomes a regime variable instead of a gate."""
    F = G.F
    L, Sg = S.signals(F, entry, 0, htf, sess, pb_ema)
    bars = G.bars
    er = efficiency_ratio(bars.close, 20).values
    atr = pd.Series(F.atr, index=bars.index)
    atr_rel = (atr / bars.close * 100)
    # volatility percentile of ATR% versus its own trailing ~2 months (no look-ahead)
    win = {"5min": 12 * 24 * 40, "15min": 4 * 24 * 40, "1h": 24 * 40, "4h": 6 * 40}[G.tf]
    vol_pct = atr_rel.rolling(win, min_periods=win // 4).rank(pct=True).values
    e = F.emas
    spread = ((e[30] - e[60]).abs() / atr).values          # how 'stretched' the stack is, in ATRs
    slope = ((e[60] - e[60].shift(10)) / atr).values        # EMA60 slope per 10 bars, in ATRs
    bi = np.where(L | Sg)[0]
    dirs = np.where(L[bi], 1, -1)
    df = pd.DataFrame(dict(bar=bi, dir=dirs, time=bars.index[bi], adx=F.adx[bi], er=er[bi], volp=vol_pct[bi],
                           spread=spread[bi], slope=slope[bi] * dirs, hour=bars.index[bi].hour))
    df["m1"] = G.pos[bi]
    df = df[G.trade_ok[df.m1.values]].reset_index(drop=True)
    return df


EXIT_SET = {
    "tp1": ([1.0], [1.0], 0, 0.0, False), "tp2": ([2.0], [1.0], 0, 0.0, False), "tp3": ([3.0], [1.0], 0, 0.0, False),
    "brk": ([999.0], [1.0], 0, 0.0, True),
    "tr1.5": ([999.0], [1.0], 0, 1.5, False), "tr2": ([999.0], [1.0], 0, 2.0, False), "tr3": ([999.0], [1.0], 0, 3.0, False),
    "tr4": ([999.0], [1.0], 0, 4.0, False), "tr6": ([999.0], [1.0], 0, 6.0, False),
    "h1brk": ([1.0, 999.0], [.5, .5], 1, 0.0, True), "h1tr3": ([1.0, 999.0], [.5, .5], 1, 3.0, False),
    "h1tr2": ([1.0, 999.0], [.5, .5], 1, 2.0, False), "h05brk": ([0.5, 999.0], [.5, .5], 1, 0.0, True),
}
SL_SET = [0.75, 1.0, 1.5, 2.0, 3.0, 4.0]


def simulate(G, ev, max_bars=60 * 24 * 10):
    F = G.F
    out = {}
    ent = ev.m1.values.astype(np.int64)
    dirs = ev.dir.values.astype(np.int64)
    lvl = G.c[ent]
    atr_at = F.atr[ev.bar.values]
    for slm in SL_SET:
        sl = atr_at * slm
        for name, (tp, fr, be, tr, brk) in EXIT_SET.items():
            r = sim_many(ent, dirs, G.o, G.h, G.l, G.c, G.mgmt, G.trend_up, G.trend_dn, G.atr1, sl, lvl,
                         np.array(tp, float), np.array(fr, float), be, tr, brk, G_.COST_RT, max_bars)
            out[(slm, name)] = r
    return out
