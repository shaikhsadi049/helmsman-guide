"""MINE engine: indicator library (TA-Lib), causal higher-TF context, rule masks -> trades by lookup, metrics, random-entry null."""
import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/bt")
import numpy as np, pandas as pd, json, talib, warnings; warnings.filterwarnings("ignore")
from numba import njit
D = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/mine/"
EXITS = json.load(open(D + "exits.json"))
D0 = pd.Timestamp("2025-01-01", tz="UTC")
_cache = {}
def m1():
    if "m1" not in _cache:
        import gcdata as G_; _cache["m1"] = G_.load_1m()
    return _cache["m1"]
def ohlcv(rule):
    """TF bars from 1m (label = bar open time); full history for indicator warm-up"""
    k = ("bars", rule)
    if k not in _cache:
        _cache[k] = m1().resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    return _cache[k]
class TF:
    """one timeframe: bars since 2024-06 aligned with the outcome table, plus full-history OHLCV for indicators"""
    def __init__(self, tf):
        self.tf = tf; self.B = pd.read_parquet(D + f"bars_{tf}.parquet")
        self.R = np.load(D + f"R_{tf}.npy", mmap_mode="r"); self.X = np.load(D + f"X_{tf}.npy", mmap_mode="r")
        full = ohlcv(tf); self.full = full
        self.pos = full.index.get_indexer(self.B.index)          # rows of the outcome table inside the full history
        assert (self.pos >= 0).all()
        self.o, self.h, self.l, self.c, self.v = (full[x].values.astype(float) for x in ("open", "high", "low", "close", "volume"))
        self.t_close = (self.B.index + pd.Timedelta(tf)).values
        self.live = (self.B.time >= D0).values
        self.month = pd.DatetimeIndex(self.B.time).tz_localize(None).to_period("M").astype(str).values
        self.quarter = pd.DatetimeIndex(self.B.time).tz_localize(None).to_period("Q").astype(str).values
        self.day = pd.DatetimeIndex(self.B.time).tz_localize(None).floor("D").values
        self.hour = pd.DatetimeIndex(self.B.index).hour.values
    def cut(self, x): return np.asarray(x, float)[self.pos]           # full-history series -> outcome-table rows
    def htf(self, rule, series_fn):
        """causal higher-TF value: the last HTF bar CLOSED at this TF bar's close"""
        b = ohlcv(rule); val = np.asarray(series_fn(b), float)
        ct = (b.index + pd.Timedelta(rule)).values
        j = np.searchsorted(ct, self.t_close, side="right") - 1
        out = val[np.clip(j, 0, len(val) - 1)]; out[j < 0] = np.nan; return out
def prank(x, n=500):
    """rolling percentile rank of the current value among the last n (market-adaptive level, 0..1)"""
    s = pd.Series(x); return s.rolling(n, min_periods=n // 4).rank(pct=True).values
def cross_up(x, lvl): x = np.asarray(x); p = np.r_[np.nan, x[:-1]]; return (p <= lvl) & (x > lvl)
def cross_dn(x, lvl): x = np.asarray(x); p = np.r_[np.nan, x[:-1]]; return (p >= lvl) & (x < lvl)
@njit(cache=True)
def greedy(bars, dirs, X, R, exit_j, live):
    """one position at a time; returns R list and bar indices of taken trades (2025+ only)"""
    n = len(bars); out_r = np.empty(n); out_b = np.empty(n, np.int64); out_d = np.empty(n, np.int64); k = 0; free = -1
    for q in range(n):
        b = bars[q]; d = 0 if dirs[q] == 1 else 1
        if not live[b]: continue
        x = X[b, d, exit_j]
        if b > free:
            r = R[b, d, exit_j]
            if r == r:
                out_r[k] = r; out_b[k] = b; out_d[k] = dirs[q]; k += 1; free = x_to_bar_dummy(x)
    return out_r[:k], out_b[:k], out_d[:k]
@njit(cache=True)
def x_to_bar_dummy(x): return x
def masks_to_signals(L, S):
    L = np.nan_to_num(L).astype(bool); S = np.nan_to_num(S).astype(bool)
    both = L & S; L = L & ~both; S = S & ~both
    b = np.where(L | S)[0]; return b, np.where(L[b], 1, -1)
class Book:
    """trades of a rule under one exit; 'free' compares 1m exit index with the next signal's 1m index"""
    pass
@njit(cache=True)
def greedy_m1(bars, dirs, m1idx, X, R, exit_j, live):
    n = len(bars); out_r = np.empty(n); out_b = np.empty(n, np.int64); out_d = np.empty(n, np.int64); k = 0; free = -1
    for q in range(n):
        b = bars[q]
        if not live[b]: continue
        d = 0 if dirs[q] == 1 else 1
        if m1idx[b] > free:
            r = R[b, d, exit_j]
            if r == r:
                out_r[k] = r; out_b[k] = b; out_d[k] = dirs[q]; k += 1; free = X[b, d, exit_j]
    return out_r[:k], out_b[:k], out_d[:k]
def evaluate(T, L, S, exits=None, min_n=40):
    """score a rule on every exit; returns list of dicts (2025-01..2026-07, one position at a time)"""
    b, d = masks_to_signals(L, S); res = []
    if len(b) == 0: return res
    m1i = T.B.m1.values.astype(np.int64); Rm = np.asarray(T.R); Xm = np.asarray(T.X)
    for j in (range(len(EXITS)) if exits is None else exits):
        r, bb, dd = greedy_m1(b, d, m1i, Xm, Rm, j, T.live)
        if len(r) < min_n: continue
        res.append(dict(exit=j, **stats(T, r, bb, dd)))
    return res
def stats(T, r, bb, dd):
    w = r > 0; eq = np.cumsum(r); dd_ = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    mon = pd.Series(r).groupby(T.month[bb]).sum(); q = pd.Series(r).groupby(T.quarter[bb]).sum()
    day = pd.Series(r).groupby(T.day[bb]).sum(); tot = r.sum()
    x = np.arange(len(eq)); r2 = np.corrcoef(x, eq)[0, 1] ** 2 * np.sign(tot) if len(eq) > 2 and eq.std() > 0 else 0
    return dict(n=len(r), win=w.mean(), PF=r[w].sum() / max(1e-9, -r[~w].sum()), sumR=tot, avgR=r.mean(), maxDD=dd_,
                score=tot / max(dd_, 1.0), mpos=(mon > 0).sum(), nmon=len(mon), qpos=(q > 0).sum(), nq=len(q), eqR2=r2,
                top5=day.nlargest(5).sum() / tot if tot > 0 else np.nan, long_R=r[dd == 1].sum(), short_R=r[dd == -1].sum(),
                n_long=(dd == 1).sum(), n_short=(dd == -1).sum())
def null_dist(T, L, S, exit_j, n_draws=200, seed=0):
    """random-entry benchmark: same number of long and short signals placed at random bars among bars allowed by the gate"""
    rng = np.random.default_rng(seed); b, d = masks_to_signals(L, S); nl, ns = (d == 1).sum(), (d == -1).sum()
    m1i = T.B.m1.values.astype(np.int64); Rm = np.asarray(T.R); Xm = np.asarray(T.X); N = len(T.B); out = []
    for _ in range(n_draws):
        bl = rng.choice(N, nl, replace=False); bs = rng.choice(N, ns, replace=False)
        bb = np.r_[bl, bs]; dd = np.r_[np.ones(nl, np.int64), -np.ones(ns, np.int64)]; o = np.argsort(bb)
        r, b2, d2 = greedy_m1(bb[o], dd[o], m1i, Xm, Rm, exit_j, T.live)
        if len(r) > 5:
            eq = np.cumsum(r); ddv = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max(); out.append((r.sum(), r.sum() / max(ddv, 1)))
    return np.array(out)
