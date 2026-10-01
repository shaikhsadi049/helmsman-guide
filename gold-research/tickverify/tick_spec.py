"""Tick verification of finding 71: each strategy's own exit (stop q, TP, BE, giveback, chandelier, H1-EMA50 flip), every tick.
usage: python tick_spec.py broker|comex"""
import sys, glob, numpy as np, pandas as pd, talib, pickle, warnings; warnings.filterwarnings("ignore")
from numba import njit, prange
DATA = sys.argv[1]; S = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad"
if DATA == "broker":
    sys.path.insert(0, S + "/dk/lab"); import lab
    m1 = pd.read_parquet(S + "/dk/m1_bid.parquet"); idx = m1.index
    fs = sorted(glob.glob(S + "/dk/hdt/*.parquet"), key=lambda f: tuple(int(x) for x in f.split("/")[-1][:-8].split("_")))
    tk = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    ts = tk.time.values.astype("datetime64[ns]").astype(np.int64); o = np.argsort(ts, kind="stable"); ts = ts[o]
    BID = tk.bid.values[o].astype(np.float64); ASK = tk.ask.values[o].astype(np.float64); del tk
    bad = (ASK - BID) <= 0; ASK[bad] = BID[bad] + 0.3; COST = 0.07
else:
    sys.path.insert(0, S + "/lab"); sys.path.insert(0, S + "/bt"); import lab, gcdata as G_, ticks as TK, dyn2_run as R2
    m1 = R2.m1; idx = R2.idx; t_ = TK.load_ticks("2024-12-15"); ts = t_.ts_event.values.astype("datetime64[ns]").astype(np.int64)
    mi = np.clip(np.searchsorted(idx.values.astype("datetime64[ns]").astype(np.int64), ts, side="right") - 1, 0, len(idx) - 1)
    BID = t_.price.values + G_.ADJ[mi]; ASK = BID; del t_; COST = G_.COST_RT
print(DATA, "ticks", len(ts), flush=True)
def tf_close(rule, f):
    b = m1.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return (b.index + pd.Timedelta(rule)).values.astype("datetime64[ns]").astype(np.int64), f(b)
h1t, h1 = tf_close("1h", lambda b: (b.close.values, talib.EMA(b.close.values, 50)))
FL = (h1[0] < h1[1]).astype(np.int8); FS = (h1[0] > h1[1]).astype(np.int8)
h4t, a4 = tf_close("4h", lambda b: talib.ATR(b.high.values, b.low.values, b.close.values, 14))
@njit(parallel=True)
def run(i0, iend, dirs, lvl, risk, tpR, be, gba, gbk, trw, flip, ts, BID, ASK, h1t, FL, FS, cost):
    n = len(i0); R = np.full(n, np.nan); XT = np.zeros(n, np.int64)
    for q in prange(n):
        s = i0[q]; e_ = iend[q]
        if s < 0 or s + 1 >= len(ts): continue
        d = dirs[q]; rk = risk[q]; L = lvl[q]
        e = ASK[s] if d == 1 else BID[s]
        stop = L - d * rk; tpx = L + d * tpR[q] * rk; best = e; ex = np.nan; xi = e_ - 1
        hp = np.searchsorted(h1t, ts[s], side="right")
        for j in range(s, e_):
            p = BID[j] if d == 1 else ASK[j]
            if (d == 1 and p <= stop) or (d == -1 and p >= stop): ex = p; xi = j; break
            if tpR[q] > 0 and ((d == 1 and p >= tpx) or (d == -1 and p <= tpx)): ex = p; xi = j; break
            if flip[q] > 0:
                while hp < len(h1t) and h1t[hp] <= ts[j]:
                    if (d == 1 and FL[hp] == 1) or (d == -1 and FS[hp] == 1): ex = p; xi = j; break
                    hp += 1
                if not np.isnan(ex): break
            if (d == 1 and p > best) or (d == -1 and p < best): best = p
            pk = (best - e) * d / rk; ns = stop
            if be[q] > 0 and pk >= be[q]:
                b2 = e + d * 0.05 * rk
                if (d == 1 and b2 > ns) or (d == -1 and b2 < ns): ns = b2
            if gba[q] > 0 and pk >= gba[q]:
                g = e + d * gbk[q] * pk * rk
                if (d == 1 and g > ns) or (d == -1 and g < ns): ns = g
            if trw[q] > 0 and pk >= 1.0:
                t = best - d * trw[q]
                if (d == 1 and t > ns) or (d == -1 and t < ns): ns = t
            if (d == 1 and ns > stop) or (d == -1 and ns < stop): stop = ns
        if np.isnan(ex): j = min(e_ - 1, len(ts) - 1); ex = BID[j] if d == 1 else ASK[j]; xi = j
        R[q] = ((ex - e) * d - cost) / rk; XT[q] = ts[xi]
    return R, XT
SPEC = {  # finding 71: sq, TP R ('q85' = market-measured), BE, giveback (a, keep), chandelier x ATR(H4), H1 flip
 "S1": ("k90", "q85", 1, (1.0, .5), 1.5, 0), "S2": ("k70", 5.0, 0, (1.5, .7), 0.0, 1), "S3": ("k90", 2.0, 1, (0, 0), 0.0, 0),
 "S4": ("k70", "q85", 0, (1.0, .5), 1.5, 1), "S5": ("k50", 3.0, 0, (2.0, .5), 0.0, 1), "S6": ("k90", "q85", 1, (1.5, .5), 0.0, 1),
 "S7": ("k50", 5.0, 1, (1.0, .5), 0.0, 1)}
SIG = lab.SIG; OUT = {}
for slot, (sq, tp, be, gb, trw, fl) in SPEC.items():
    allr = np.where(SIG.slot.values == slot)[0]; sa = SIG.iloc[allr]
    k = np.clip(sa[sq].values, 0.5, 8.0)
    if tp == "q85":
        mfeR = sa.mfe_a.values / k; xe = sa.xend.values; mm = sa.m1.values; tpv = np.full(len(allr), 3.0)
        for i in range(len(allr)):
            past = xe[:i] < mm[i]
            if past.sum() >= 30: tpv[i] = np.quantile(mfeR[:i][past], 0.85)
        tpv = np.clip(tpv, 0.5, 8.0)
    else: tpv = np.full(len(allr), float(tp))
    live = (lab.TIME[allr] >= lab.D0); rows = allr[live]; s = SIG.iloc[rows]; n = len(rows)
    tin = (idx[s.m1.values] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64)
    i0 = np.searchsorted(ts, tin, side="left"); iend = np.searchsorted(ts, tin + 14400 * 60 * 10**9)
    a4v = a4[np.clip(np.searchsorted(h4t, tin, side="right") - 1, 0, len(a4) - 1)]
    risk = k[live] * s.atr.values
    R, XT = run(i0.astype(np.int64), iend.astype(np.int64), s.dir.values.astype(np.int64), s.lvl.values.astype(np.float64), risk, tpv[live],
                np.full(n, float(be)), np.full(n, gb[0]), np.full(n, gb[1]), np.nan_to_num(trw * a4v, nan=0.0), np.full(n, fl, np.int64),
                ts, BID, ASK, h1t, FL, FS, COST)
    m1x = np.clip(np.searchsorted(idx.values.astype("datetime64[ns]").astype(np.int64), XT, side="right") - 1, 0, len(idx) - 1)
    OUT[slot] = dict(rows=rows, R=R, X=m1x, risk=risk); print(slot, "sum R (all signals)", round(np.nansum(R), 1), flush=True)
pickle.dump(OUT, open(f"tick_spec_{DATA}.pkl", "wb"))
