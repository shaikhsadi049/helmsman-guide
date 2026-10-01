"""Extended exit research: trails (chandelier TF/H1/H4, PSAR, Donchian, EMA, Kijun, step), breakeven variants,
stall exits (no new high for N bars / no progress after T), giveback exits. Works for any signal list (m1 index, dir, lvl, risk)."""
import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/bt")
import numpy as np, pandas as pd, talib, itertools
from numba import njit, prange
import gcdata as G_
_m1 = G_.load_1m(); IDX = _m1.index
O, H, L, C = (_m1[x].values for x in ("open", "high", "low", "close"))
def on_grid(rule, fn):
    """value of the last CLOSED bar of `rule`, placed on every 1m bar (causal), plus a flag where a bar just closed"""
    b = _m1.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    val = np.asarray(fn(b), float); ct = (b.index + pd.Timedelta(rule)).values
    j = np.searchsorted(ct, (IDX + pd.Timedelta(minutes=1)).values, side="right") - 1
    out = np.where(j >= 0, val[np.clip(j, 0, len(val) - 1)], np.nan)
    flag = np.r_[False, j[1:] != j[:-1]]
    return out, flag
_grid = {}
def grid(name):
    """trail reference arrays; long version (support) and short version (resistance)"""
    if name in _grid: return _grid[name]
    tf, kind, p = name.split(":"); p = float(p)
    if kind == "atr": f = lambda b: talib.ATR(b.high.values, b.low.values, b.close.values, 14)
    elif kind == "sar": f = lambda b: talib.SAR(b.high.values, b.low.values, 0.02 * p, 0.2)
    elif kind == "dlo": f = lambda b: pd.Series(b.low.values).rolling(int(p)).min().values
    elif kind == "dhi": f = lambda b: pd.Series(b.high.values).rolling(int(p)).max().values
    elif kind == "ema": f = lambda b: talib.EMA(b.close.values, int(p))
    elif kind == "kijun": f = lambda b: (pd.Series(b.high.values).rolling(int(p)).max().values + pd.Series(b.low.values).rolling(int(p)).min().values) / 2
    _grid[name] = on_grid(tf, f); return _grid[name]
# trail codes: 0 none, 1 chandelier from best (width array), 2 level-trail long/short arrays (SAR/Donchian/EMA/Kijun), 3 step 1R
@njit(cache=True)
def sim(i0, pos, lvl, risk, tp, beR, beOff, tcode, wid, levL, levS, buf, stallN, flag, prog_T, prog_R, gbA, gbG, hor, o, h, l, c, cost):
    n = len(o); i = i0 + 1
    if i >= n: return np.nan, i0
    e = o[i]; stop = lvl - pos * risk; tpx = lvl + pos * tp * risk; best = e; nb = 0; since_new = 0; end = min(n, i + hor); peak = 0.0
    while i < end:
        if (pos == 1 and o[i] <= stop) or (pos == -1 and o[i] >= stop): return ((o[i] - e) * pos - cost) / risk, i
        hf = (h[i] - o[i]) < (o[i] - l[i]); ff = (pos == 1 and hf) or (pos == -1 and not hf)
        fe = h[i] if pos == 1 else l[i]; ae = l[i] if pos == 1 else h[i]
        for ph in range(2):
            if (ph == 0) == ff:
                if tp > 0 and ((pos == 1 and fe >= tpx) or (pos == -1 and fe <= tpx)):
                    px = o[i] if ((pos == 1 and o[i] >= tpx) or (pos == -1 and o[i] <= tpx)) else tpx
                    return ((px - e) * pos - cost) / risk, i
            else:
                if (pos == 1 and ae <= stop) or (pos == -1 and ae >= stop): return ((stop - e) * pos - cost) / risk, i
        nbst = max(best, h[i]) if pos == 1 else min(best, l[i])
        if nbst != best: since_new = 0
        best = nbst; prof = (best - e) * pos
        if prof / risk > peak: peak = prof / risk
        if flag[i]:
            nb += 1; since_new += 1
            if stallN > 0 and since_new >= stallN and (c[i] - e) * pos > 0:      # stalled in profit: book it
                return ((c[i] - e) * pos - cost) / risk, i
            if prog_T > 0 and nb == prog_T and (c[i] - e) * pos < prog_R * risk:  # no progress: leave
                return ((c[i] - e) * pos - cost) / risk, i
        if beR > 0 and prof >= beR * risk:
            ns = e + pos * beOff * risk
            if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        if tcode == 1 and wid[i] == wid[i]:
            ns = best - pos * wid[i]
            if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        elif tcode == 2:
            lv = levL[i] if pos == 1 else levS[i]
            if lv == lv:
                ns = lv - pos * buf * risk
                if ((pos == 1 and ns > stop and ns < c[i]) or (pos == -1 and ns < stop and ns > c[i])) and prof > 0: stop = ns
        elif tcode == 3:
            steps = int(prof / risk)
            if steps >= 1:
                ns = e + pos * (steps - 1) * risk
                if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        if gbA > 0 and peak >= gbA and (c[i] - e) * pos / risk < (1 - gbG) * peak:  # gave back too much of the peak
            return ((c[i] - e) * pos - cost) / risk, i
        i += 1
    j = min(i, n - 1); return ((c[j] - e) * pos - cost) / risk, j
@njit(parallel=True, cache=True)
def sim_all(m, dirs, lvl, risk, tp, beR, beOff, tcode, wid, levL, levS, buf, stallN, flag, prog_T, prog_R, gbA, gbG, hor, o, h, l, c, cost):
    K = len(m); R = np.empty(K, np.float32); X = np.empty(K, np.int64)
    for k in prange(K):
        r, x = sim(m[k], dirs[k], lvl[k], risk[k], tp[k], beR, beOff, tcode, wid, levL, levS, buf, stallN, flag, prog_T, prog_R, gbA, gbG, hor[k], o, h, l, c, cost)
        R[k] = r; X[k] = x
    return R, X
NAN = np.full(len(O), np.nan)
def run(m, dirs, lvl, risk, hor, tp=0.0, be=(0, 0), trail=None, buf=0.0, stall=0, prog=(0, 0.0), gb=(0, 0.0), tf_flag="15min", cost=G_.COST_RT):
    """trail: None | ("chand", grid_atr_name, mult) | ("lev", long_grid_name, short_grid_name) | ("step",)"""
    tcode, wid, lL, lS = 0, NAN, NAN, NAN
    if trail is not None:
        if trail[0] == "chand": tcode = 1; wid = grid(trail[1])[0] * trail[2]
        elif trail[0] == "lev": tcode = 2; lL = grid(trail[1])[0]; lS = grid(trail[2])[0]
        elif trail[0] == "step": tcode = 3
    flag = grid(f"{tf_flag}:atr:14")[1]
    tpv = np.full(len(m), float(tp)) if np.isscalar(tp) else np.asarray(tp, float)
    return sim_all(np.asarray(m, np.int64), np.asarray(dirs, np.int64), np.asarray(lvl, float), np.asarray(risk, float), tpv, float(be[0]), float(be[1]),
                   tcode, wid, lL, lS, float(buf), int(stall), flag, int(prog[0]), float(prog[1]), float(gb[0]), float(gb[1]), np.asarray(hor, np.int64), O, H, L, C, cost)
def exit_menu(tf):
    """the structured menu of exits tried for a signal stream on timeframe tf"""
    M = []
    for tp in (0, 2, 3, 5):
        for be in ((0, 0), (1.0, 0.05), (0.5, 0.0), (1.5, 0.5)):
            for tr in (None, ("chand", f"{tf}:atr:14", 2.0), ("chand", f"{tf}:atr:14", 3.0), ("chand", f"{tf}:atr:14", 5.0),
                       ("chand", "1h:atr:14", 2.0), ("chand", "4h:atr:14", 1.5), ("chand", "4h:atr:14", 3.0),
                       ("lev", f"{tf}:sar:1", f"{tf}:sar:1"), ("lev", f"{tf}:dlo:10", f"{tf}:dhi:10"), ("lev", f"{tf}:dlo:20", f"{tf}:dhi:20"),
                       ("lev", f"{tf}:ema:20", f"{tf}:ema:20"), ("lev", f"{tf}:ema:50", f"{tf}:ema:50"), ("lev", f"{tf}:kijun:26", f"{tf}:kijun:26"),
                       ("lev", "1h:dlo:10", "1h:dhi:10"), ("lev", "4h:kijun:26", "4h:kijun:26"), ("step",)):
                M.append(dict(tp=tp, be=be, trail=tr))
    extra = []
    for base in ({"tp": 0, "be": (1.0, 0.05), "trail": ("chand", f"{tf}:atr:14", 3.0)}, {"tp": 3, "be": (1.0, 0.05), "trail": None}):
        for stall in (6, 12, 24): extra.append(dict(base, stall=stall))
        for prog in ((6, 0.3), (12, 0.3), (24, 0.0)): extra.append(dict(base, prog=prog))
        for gb in ((1.0, 0.5), (2.0, 0.5), (2.0, 0.3), (3.0, 0.4)): extra.append(dict(base, gb=gb))
    return M + extra
def describe(x):
    s = []
    s.append(f"TP {x['tp']}R" if x["tp"] else "no TP")
    if x["be"][0]: s.append(f"BE: after +{x['be'][0]}R stop to +{x['be'][1]}R")
    tr = x["trail"]
    if tr is None: s.append("no trail")
    elif tr[0] == "chand": s.append(f"chandelier {tr[2]}x ATR14({tr[1].split(':')[0]}) from best price")
    elif tr[0] == "lev": s.append(f"trail at {tr[1].split(':')[1].upper()}({tr[1].split(':')[2]}) of {tr[1].split(':')[0]} (once in profit)")
    else: s.append("step trail: stop = entry + (whole R gained - 1)R")
    if x.get("stall"): s.append(f"stall exit: book profit if no new extreme for {x['stall']} TF bars")
    if x.get("prog"): s.append(f"no-progress exit: after {x['prog'][0]} TF bars leave if profit < {x['prog'][1]}R")
    if x.get("gb"): s.append(f"giveback exit: after peak >= {x['gb'][0]}R leave if profit falls below {(1-x['gb'][1]):.0%} of peak")
    return "; ".join(s)
