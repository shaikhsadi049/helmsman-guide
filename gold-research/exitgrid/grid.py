"""Exit grid: every trend signal x 1080 exit combos on 1m bid/ask (broker) or trade (COMEX) bars. Pessimistic intrabar order (adverse first).
usage: python grid.py broker|comex"""
import sys, itertools, numpy as np, pandas as pd, talib, warnings; warnings.filterwarnings("ignore")
from numba import njit, prange
DATA = sys.argv[1]; S = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad"
if DATA == "broker":
    sys.path.insert(0, S + "/dk/lab"); import lab
    m1 = pd.read_parquet(S + "/dk/m1_bid.parquet"); sp = pd.read_parquet(S + "/dk/m1_spread.parquet").spread
    spr = sp.reindex(m1.index).ffill().fillna(sp.median()).clip(0.05, 3.0).values; COST = 0.07
else:
    sys.path.insert(0, S + "/lab"); sys.path.insert(0, S + "/bt"); import lab, dyn2_run as R2, gcdata as G_
    m1 = R2.m1.copy()                       # already Panama back-adjusted
    spr = np.zeros(len(m1)); COST = G_.COST_RT
SIG = lab.SIG; o, h, l, c = (m1[x].values.astype(np.float64) for x in ("open", "high", "low", "close")); n = len(m1)
def tf_arr(rule, f):
    b = m1.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    v = f(b); end = b.index + pd.Timedelta(rule); pos = np.searchsorted(m1.index.values, end.values, side="left") - 1
    out = np.full(n, np.nan); out[pos[pos >= 0]] = v[pos >= 0]; return pd.Series(out).ffill().values, pos
atr4, _ = tf_arr("4h", lambda b: talib.ATR(b.high.values, b.low.values, b.close.values, 14))
h1c, p1 = tf_arr("1h", lambda b: b.close.values); h1e, _ = tf_arr("1h", lambda b: talib.EMA(b.close.values, 50))
flipL = np.zeros(n, np.bool_); flipS = np.zeros(n, np.bool_); pp = p1[p1 >= 0]
flipL[pp] = h1c[pp] < h1e[pp]; flipS[pp] = h1c[pp] > h1e[pp]          # evaluated only at H1 closes
TREND = [s for s in ("S1", "S2", "S3", "S4", "S5", "S6", "S7")]
rows = np.where(SIG.slot.isin(TREND).values)[0]; s = SIG.iloc[rows]
SQS = ("k50", "k70", "k90")
# market-measured q0.85 target per signal & stop quantile (past resolved signals of the same slot)
q85 = np.full((len(rows), 3), 3.0)
for si, sq in enumerate(SQS):
    k = np.clip(s[sq].values, 0.5, 8.0); mfeR = s.mfe_a.values / k
    for slot in TREND:
        ii = np.where(s.slot.values == slot)[0]; xe = s.xend.values[ii]; mm = s.m1.values[ii]
        for j, i in enumerate(ii):
            past = xe[:j] < mm[j]
            if past.sum() >= 30: q85[i, si] = np.quantile(mfeR[ii[:j]][past], 0.85)
q85 = np.clip(q85, 0.5, 8.0)
TPS = ("none", "2R", "3R", "5R", "q85"); BES = (0.0, 1.0); GBS = ((0, 0), (1.0, .5), (1.5, .5), (2.0, .5), (1.5, .7), (3.0, .5))
TRS = (0.0, 1.5, 3.0); FLS = (0, 1)
COMBOS = list(itertools.product(range(3), range(5), BES, range(len(GBS)), TRS, FLS))
cs = np.array([[a, b, be, GBS[g][0], GBS[g][1], tr, fl] for a, b, be, g, tr, fl in COMBOS], np.float64)
@njit(parallel=True)
def run(i0, dirs, lvl, risk3, tp3, a4, o, h, l, c, spr, flipL, flipS, cs, cost, hor):
    N = len(i0); K = cs.shape[0]; R = np.full((N, K), np.nan, np.float32); X = np.zeros((N, K), np.int32)
    for q in prange(N * K):
        i = q // K; k = q % K; st = i0[i]
        if st >= len(o) - 1: continue
        sq = int(cs[k, 0]); tpk = int(cs[k, 1]); be = cs[k, 2]; ga = cs[k, 3]; gb = cs[k, 4]; trw = cs[k, 5]; fl = cs[k, 6]
        d = dirs[i]; rk = risk3[i, sq]; L = lvl[i]
        sm = 1.0 if d == -1 else 0.0                                       # short path = ask = bid + spread
        e = o[st] + spr[st] if d == 1 else o[st]                         # long buys at ask, short sells at bid
        stop = L - d * rk
        tpR = 0.0
        if tpk == 1: tpR = 2.0
        elif tpk == 2: tpR = 3.0
        elif tpk == 3: tpR = 5.0
        elif tpk == 4: tpR = tp3[i, sq]
        tpx = L + d * tpR * rk; best = e; wid = trw * a4[st]; end = min(len(o), st + hor); ex = np.nan; xi = end - 1
        for j in range(st, end):
            sj = sm * spr[j]; oj = o[j] + sj; hj = h[j] + sj; lj = l[j] + sj; cj = c[j] + sj
            if j > st and ((d == 1 and oj <= stop) or (d == -1 and oj >= stop)): ex = oj; xi = j; break
            ae = lj if d == 1 else hj; fe = hj if d == 1 else lj
            if (d == 1 and ae <= stop) or (d == -1 and ae >= stop): ex = stop; xi = j; break
            if tpR > 0 and ((d == 1 and fe >= tpx) or (d == -1 and fe <= tpx)): ex = tpx; xi = j; break
            if (d == 1 and fe > best) or (d == -1 and fe < best): best = fe
            pk = (best - e) * d / rk
            ns = stop
            if be > 0 and pk >= be: ns = e + d * 0.05 * rk if d == 1 else e - 0.05 * rk
            if ga > 0 and pk >= ga:
                g = e + d * gb * pk * rk
                if (d == 1 and g > ns) or (d == -1 and g < ns): ns = g
            if trw > 0 and pk >= 1.0:
                t = best - d * wid
                if (d == 1 and t > ns) or (d == -1 and t < ns): ns = t
            if (d == 1 and ns > stop) or (d == -1 and ns < stop): stop = ns
            if fl > 0 and ((d == 1 and flipL[j]) or (d == -1 and flipS[j])): ex = cj; xi = j; break
        if np.isnan(ex): ex = c[end - 1] + sm * spr[end - 1]
        R[i, k] = ((ex - e) * d - cost) / rk; X[i, k] = xi
    return R, X
i0 = s.m1.values.astype(np.int64) + 1
risk3 = np.stack([np.clip(s[q].values, 0.5, 8.0) * s.atr.values for q in SQS], 1)
import time; t0 = time.time()
R, X = run(i0, s.dir.values.astype(np.int64), s.lvl.values.astype(np.float64), risk3, q85, np.nan_to_num(atr4, nan=5.0), o, h, l, c, spr, flipL, flipS, cs, COST, 14400)
print(DATA, "signals", len(rows), "combos", len(COMBOS), "time", round(time.time() - t0), "s", flush=True)
np.save(f"R_{DATA}.npy", R); np.save(f"X_{DATA}.npy", X); np.save(f"rows_{DATA}.npy", rows)
pd.DataFrame(COMBOS, columns=["sq", "tp", "be", "gb", "trail", "flip"]).assign(sq=lambda d: d.sq.map(dict(enumerate(SQS))), tp=lambda d: d.tp.map(dict(enumerate(TPS))),
    gb=lambda d: d.gb.map(lambda g: "none" if g == 0 else f"{GBS[g][0]}R/{GBS[g][1]}")).to_csv("combos.csv", index=False)
