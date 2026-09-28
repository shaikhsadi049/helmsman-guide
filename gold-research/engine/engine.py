"""Bar-by-bar backtester for DTC-style strategies on XAUUSD (numba).

Semantics mirror TradingView's broker emulator:
- signal on bar i close -> market fill at open of bar i+1
- SL/TP levels are computed from close[i] (as in the Pine scripts)
- intrabar path: if high is closer to open than low -> O,H,L,C else O,L,H,C
- gaps: stop/limit already beyond the open fill at the open
Position size is fixed at 1 oz; results are in USD and in R (initial risk units).
"""
import numpy as np
import pandas as pd
from numba import njit

DATA = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/data"


# ---------------------------------------------------------------- data
def load_m15():
    d = pd.read_csv(f"{DATA}/historical-data/XAUUSD/XAUUSDm15.csv", parse_dates=["Date"])
    d = d.rename(columns={"Date": "time"}).set_index("time")
    for c in ["open", "high", "low", "close"]:
        d[c] = d[c] / 100.0
    return d[["open", "high", "low", "close"]]


def load_h1_2026():
    d = pd.read_csv(f"{DATA}/xauusd-1h-ohlcv-metals-historical-data/XAUUSD_1h.csv")
    d["time"] = pd.to_datetime(d["datetime"], utc=True).dt.tz_localize(None)
    return d.set_index("time")[["open", "high", "low", "close"]]


def resample(df, rule):
    return df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


# ---------------------------------------------------------------- indicators (TradingView-equivalent)
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rma(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def atr(df, n=14):
    pc = df.close.shift(1)
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    tr.iloc[0] = df.high.iloc[0] - df.low.iloc[0]
    return rma(tr, n)


def adx(df, n=14):
    up = df.high.diff()
    dn = -df.low.diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = atr(df, n)
    pdi = 100 * rma(pd.Series(plus, index=df.index), n) / tr
    mdi = 100 * rma(pd.Series(minus, index=df.index), n) / tr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return rma(dx.fillna(0), n), pdi, mdi


def htf_bull(df, rule, fast=20, slow=50):
    """Previous *closed* HTF bar: EMA fast > EMA slow, mapped onto df's index (no repaint)."""
    h = resample(df, rule)
    bull = (ema(h.close, fast) > ema(h.close, slow)).shift(1)
    key = df.index.floor(rule) if rule not in ("1D",) else df.index.normalize()
    return pd.Series(bull.reindex(key).values, index=df.index).fillna(False).astype(bool)


# ---------------------------------------------------------------- engine
@njit(cache=True)
def run(o, h, l, c, long_sig, short_sig, trend_up, trend_dn,
        sl_long, sl_short, tp_r, tp_frac, be_leg, trail_atr, atr_arr,
        exit_on_break, reverse, cost_rt):
    """Returns trades array: [entry_i, exit_i, dir, pnl_usd, risk_usd]."""
    n = len(o)
    out = np.zeros((n, 5))
    nt = 0
    nlegs = len(tp_r)

    pos = 0
    entry_px = 0.0
    risk = 0.0
    stop = 0.0
    tps = np.zeros(nlegs)
    rem = np.zeros(nlegs)          # remaining size per leg
    pnl = 0.0
    entry_i = 0
    best = 0.0                     # best price since entry (for trailing)
    legs_done = 0

    pend = 0                       # pending entry direction for next open
    pend_lvl_c = 0.0
    pend_sl = 0.0
    pend_exit = False              # pending market exit at next open

    for i in range(n):
        # ---- 1) market orders at the open
        if pos != 0 and (pend_exit or (pend != 0 and pend != pos)):
            left = rem.sum()
            fill = o[i]
            pnl += (fill - entry_px) * pos * left - cost_rt * left
            out[nt, 0] = entry_i; out[nt, 1] = i; out[nt, 2] = pos
            out[nt, 3] = pnl; out[nt, 4] = risk
            nt += 1
            pos = 0
        pend_exit = False
        if pend != 0 and pos == 0:
            pos = pend
            entry_px = o[i]
            risk = pend_sl
            stop = pend_lvl_c - pos * pend_sl
            for k in range(nlegs):
                tps[k] = pend_lvl_c + pos * tp_r[k] * pend_sl
                rem[k] = tp_frac[k]
            pnl = 0.0
            entry_i = i
            best = entry_px
            legs_done = 0
        pend = 0

        # ---- 2) intrabar stop / limit fills
        if pos != 0:
            closed = False
            # gap through stop at the open
            if (pos == 1 and o[i] <= stop) or (pos == -1 and o[i] >= stop):
                left = rem.sum()
                pnl += (o[i] - entry_px) * pos * left - cost_rt * left
                rem[:] = 0.0
                closed = True
            else:
                high_first = (h[i] - o[i]) < (o[i] - l[i])
                fav_first = (pos == 1 and high_first) or (pos == -1 and not high_first)
                fav_ext = h[i] if pos == 1 else l[i]
                adv_ext = l[i] if pos == 1 else h[i]
                for phase in range(2):
                    do_fav = (phase == 0) == fav_first
                    if do_fav:
                        for k in range(nlegs):
                            if rem[k] > 0 and tp_r[k] < 900:
                                hit = (fav_ext >= tps[k]) if pos == 1 else (fav_ext <= tps[k])
                                if hit:
                                    gap = (o[i] >= tps[k]) if pos == 1 else (o[i] <= tps[k])
                                    px = o[i] if gap else tps[k]
                                    pnl += (px - entry_px) * pos * rem[k] - cost_rt * rem[k]
                                    rem[k] = 0.0
                                    legs_done += 1
                    else:
                        hit = (adv_ext <= stop) if pos == 1 else (adv_ext >= stop)
                        if hit:
                            left = rem.sum()
                            pnl += (stop - entry_px) * pos * left - cost_rt * left
                            rem[:] = 0.0
                    if rem.sum() <= 1e-9:
                        closed = True
                        break
            if closed:
                out[nt, 0] = entry_i; out[nt, 1] = i; out[nt, 2] = pos
                out[nt, 3] = pnl; out[nt, 4] = risk
                nt += 1
                pos = 0
            else:
                # ---- 3) bar-close management (effective from next bar)
                if be_leg > 0 and legs_done >= be_leg:
                    if pos == 1 and stop < entry_px:
                        stop = entry_px
                    if pos == -1 and stop > entry_px:
                        stop = entry_px
                if trail_atr > 0:
                    if pos == 1:
                        best = max(best, h[i])
                        ns = best - trail_atr * atr_arr[i]
                        if ns > stop:
                            stop = ns
                    else:
                        best = min(best, l[i])
                        ns = best + trail_atr * atr_arr[i]
                        if ns < stop:
                            stop = ns
                if exit_on_break:
                    if (pos == 1 and not trend_up[i]) or (pos == -1 and not trend_dn[i]):
                        pend_exit = True

        # ---- 4) new signals at the close
        if i + 1 < n:
            if long_sig[i] and (pos == 0 or (pos == -1 and reverse)):
                pend = 1; pend_lvl_c = c[i]; pend_sl = sl_long[i]
            elif short_sig[i] and (pos == 0 or (pos == 1 and reverse)):
                pend = -1; pend_lvl_c = c[i]; pend_sl = sl_short[i]
            if pend != 0 and not (pend_sl > 0):
                pend = 0
    return out[:nt]


# ---------------------------------------------------------------- stats
def stats(tr, index, years=None):
    if len(tr) == 0:
        return dict(trades=0)
    pnl = tr[:, 3]
    R = pnl / tr[:, 4]
    wins = pnl > 0
    gp = pnl[wins].sum()
    gl = -pnl[~wins].sum()
    eqR = np.cumsum(R)
    ddR = (np.maximum.accumulate(np.concatenate([[0], eqR]))[1:] - eqR).max()
    span_years = (index[-1] - index[0]).days / 365.25
    t_entry = index[tr[:, 0].astype(int)]
    yr = pd.Series(R, index=t_entry).groupby(t_entry.year).sum()
    return dict(
        trades=len(tr), per_year=len(tr) / span_years,
        win=wins.mean() * 100, pf=gp / gl if gl > 0 else np.inf,
        expR=R.mean(), totR=R.sum(), ddR=ddR,
        usd=pnl.sum(), years_pos=(yr > 0).mean() * 100, worst_yearR=yr.min(),
        long_R=R[tr[:, 2] == 1].sum(), short_R=R[tr[:, 2] == -1].sum(),
    )
