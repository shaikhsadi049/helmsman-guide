"""GC (COMEX gold) real data: back-adjusted 1m bars, TF features mapped onto a 1m execution grid,
and a tick-level execution path for final validation."""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from numba import njit
import engine as E

GC = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/data/gc"
TRADE_START = pd.Timestamp("2024-08-01", tz="UTC")
COST_RT = 0.34


def load_1m():
    d = pd.concat([pd.read_parquet(f"{GC}/GC_OHLCV1M_{y}.parquet") for y in range(2022, 2027)])
    d = d[~d.index.duplicated()].sort_index()
    inst = d.instrument_id.values
    adj = np.zeros(len(d))
    rolls = []
    for i in np.where(inst[1:] != inst[:-1])[0] + 1:
        gap = d.open.values[i] - d.close.values[i - 1]
        adj[:i] += gap                      # Panama back-adjust: shift history onto the newest contract
        rolls.append((d.index[i], gap))
    for c in ["open", "high", "low", "close"]:
        d[c] = d[c].values + adj
    out = d[["open", "high", "low", "close", "volume"]].copy()
    out.attrs = {}
    global ROLLS, ADJ
    ROLLS = rolls
    ADJ = adj
    return out


class Grid:
    """Features on a signal timeframe, placed on the 1m execution grid."""

    def __init__(self, m1, tf):
        import strat as S
        self.m1 = m1
        self.tf = tf
        bars = E.resample(m1, tf)
        self.bars = bars
        self.F = S.Feat(bars)
        # 1m index of the last minute inside each TF bar (signal/mgmt happen at its close)
        end = bars.index + pd.Timedelta(tf)
        pos = np.searchsorted(m1.index.values, end.values, side="left") - 1
        self.pos = pos
        n = len(m1)
        self.o, self.h, self.l, self.c = (m1.open.values, m1.high.values, m1.low.values, m1.close.values)
        self.mgmt = np.zeros(n, bool)
        self.mgmt[pos] = True
        # forward-fill TF values from their close minute onward
        idx = np.full(n, -1)
        idx[pos] = np.arange(len(pos))
        idx = pd.Series(idx).replace(-1, np.nan).ffill().fillna(0).astype(int).values
        self.idx = idx
        self.trend_up = self.F.bull[idx]
        self.trend_dn = self.F.bear[idx]
        self.atr1 = self.F.atr[idx]
        self.trade_ok = (m1.index >= TRADE_START)

    def place(self, a, fill=False):
        out = np.zeros(len(self.m1), dtype=a.dtype) if not fill else np.full(len(self.m1), 0.0)
        out[self.pos] = a
        return out


@njit(cache=True)
def run2(o, h, l, c, long_sig, short_sig, trend_up, trend_dn, mgmt,
         sl_long, sl_short, tp_r, tp_frac, be_leg, trail_atr, atr_arr, exit_on_break, reverse, cost_rt):
    """Same as engine.run but BE / trailing / trend-break management happens only on mgmt bars
    (signal-timeframe closes), while fills are checked on every 1m bar."""
    n = len(o)
    out = np.zeros((n, 5))
    nt = 0
    nlegs = len(tp_r)
    pos = 0; entry_px = 0.0; risk = 0.0; stop = 0.0
    tps = np.zeros(nlegs); rem = np.zeros(nlegs)
    pnl = 0.0; entry_i = 0; best = 0.0; legs_done = 0
    pend = 0; pend_lvl_c = 0.0; pend_sl = 0.0; pend_exit = False
    for i in range(n):
        if pos != 0 and (pend_exit or (pend != 0 and pend != pos)):
            left = rem.sum()
            pnl += (o[i] - entry_px) * pos * left - cost_rt * left
            out[nt, 0] = entry_i; out[nt, 1] = i; out[nt, 2] = pos; out[nt, 3] = pnl; out[nt, 4] = risk
            nt += 1; pos = 0
        pend_exit = False
        if pend != 0 and pos == 0:
            pos = pend; entry_px = o[i]; risk = pend_sl
            stop = pend_lvl_c - pos * pend_sl
            for k in range(nlegs):
                tps[k] = pend_lvl_c + pos * tp_r[k] * pend_sl
                rem[k] = tp_frac[k]
            pnl = 0.0; entry_i = i; best = entry_px; legs_done = 0
        pend = 0
        if pos != 0:
            closed = False
            if (pos == 1 and o[i] <= stop) or (pos == -1 and o[i] >= stop):
                left = rem.sum(); pnl += (o[i] - entry_px) * pos * left - cost_rt * left
                rem[:] = 0.0; closed = True
            else:
                high_first = (h[i] - o[i]) < (o[i] - l[i])
                fav_first = (pos == 1 and high_first) or (pos == -1 and not high_first)
                fav_ext = h[i] if pos == 1 else l[i]
                adv_ext = l[i] if pos == 1 else h[i]
                for phase in range(2):
                    if (phase == 0) == fav_first:
                        for k in range(nlegs):
                            if rem[k] > 0 and tp_r[k] < 900:
                                hit = (fav_ext >= tps[k]) if pos == 1 else (fav_ext <= tps[k])
                                if hit:
                                    gap = (o[i] >= tps[k]) if pos == 1 else (o[i] <= tps[k])
                                    px = o[i] if gap else tps[k]
                                    pnl += (px - entry_px) * pos * rem[k] - cost_rt * rem[k]
                                    rem[k] = 0.0; legs_done += 1
                    else:
                        hit = (adv_ext <= stop) if pos == 1 else (adv_ext >= stop)
                        if hit:
                            left = rem.sum(); pnl += (stop - entry_px) * pos * left - cost_rt * left
                            rem[:] = 0.0
                    if rem.sum() <= 1e-9:
                        closed = True; break
            if closed:
                out[nt, 0] = entry_i; out[nt, 1] = i; out[nt, 2] = pos; out[nt, 3] = pnl; out[nt, 4] = risk
                nt += 1; pos = 0
            elif mgmt[i]:
                if be_leg > 0 and legs_done >= be_leg:
                    if pos == 1 and stop < entry_px: stop = entry_px
                    if pos == -1 and stop > entry_px: stop = entry_px
                if trail_atr > 0:
                    if pos == 1:
                        best = max(best, h[i]); ns = best - trail_atr * atr_arr[i]
                        if ns > stop: stop = ns
                    else:
                        best = min(best, l[i]); ns = best + trail_atr * atr_arr[i]
                        if ns < stop: stop = ns
                if exit_on_break:
                    if (pos == 1 and not trend_up[i]) or (pos == -1 and not trend_dn[i]):
                        pend_exit = True
        elif pos != 0 and trail_atr > 0:
            pass
        if pos != 0 and trail_atr > 0:
            if pos == 1: best = max(best, h[i])
            else: best = min(best, l[i])
        if i + 1 < n and mgmt[i]:
            if long_sig[i] and (pos == 0 or (pos == -1 and reverse)):
                pend = 1; pend_lvl_c = c[i]; pend_sl = sl_long[i]
            elif short_sig[i] and (pos == 0 or (pos == 1 and reverse)):
                pend = -1; pend_lvl_c = c[i]; pend_sl = sl_short[i]
            if pend != 0 and not (pend_sl > 0):
                pend = 0
    return out[:nt]


def backtest(G, entry="swing", adx_min=0, htf=(), sess=None, pb_ema=30, sl="atr", sl_val=2.0, swing_n=8,
             exit="brk", reverse=True, cost=COST_RT, orig_atr_filter=True):
    import strat as S
    L, Sg = S.signals(G.F, entry, adx_min, htf, sess, pb_ema, orig_atr_filter)
    dl, ds = S.stops(G.F, sl, sl_val, swing_n)
    Lm = G.place(L) & G.trade_ok
    Sm = G.place(Sg) & G.trade_ok
    x = S.exit_cfg(exit)
    return run2(G.o, G.h, G.l, G.c, Lm, Sm, G.trend_up, G.trend_dn, G.mgmt,
                G.place(dl.astype(float), True), G.place(ds.astype(float), True),
                np.array(x["tp_r"], float), np.array(x["tp_frac"], float), x["be_leg"], x["trail"],
                G.atr1, x["brk"], reverse, cost)
