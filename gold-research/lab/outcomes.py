"""LAB step 3: every signal x every exit policy on the 1m path (O-H-L-C order, gap fills, cost $0.34/oz).
Policy = stop quantile, target, partial, breakeven, trail kind/width, profit ratchet, time stop."""
import sys; sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, itertools, json, warnings; warnings.filterwarnings("ignore")
from numba import njit, prange
import dyn2_run as R2, gcdata as G_
SIG = pd.read_parquet("signals.parquet"); n = len(SIG)
o = R2.m1.open.values; h = R2.m1.high.values; l = R2.m1.low.values; c = R2.m1.close.values
G4 = R2.G4; h4close = G4.mgmt.astype(np.bool_)          # 1m bars where an H4 bar closes
@njit(cache=True)
def sim_one(i0, pos, lvl, risk, tp, pf, pR, lockR, beR, beL, tkind, tw, ra, rk, tsT, tsR, hor, o, h, l, c, h4c, cost):
    """returns R, exit bar, mfe R, first bar the stop is at/after entry (-1 never)"""
    n = len(o); i = i0 + 1
    if i >= n: return np.nan, i0, 0.0, -1
    entry = o[i]; stop = lvl - pos * risk; size = 1.0; pnl = 0.0; best = entry; mfe = 0.0; part_done = pf <= 0; lk = -1
    tpx = lvl + pos * tp * risk if tp > 0 else np.nan; ppx = lvl + pos * pR * risk
    end = min(n, i + hor); closed = False
    while i < end:
        # gap through stop at the open
        if (pos == 1 and o[i] <= stop) or (pos == -1 and o[i] >= stop):
            pnl += ((o[i] - entry) * pos - cost) * size; closed = True; break
        hf = (h[i] - o[i]) < (o[i] - l[i]); fav_first = (pos == 1 and hf) or (pos == -1 and not hf)
        fe = h[i] if pos == 1 else l[i]; ae = l[i] if pos == 1 else h[i]
        for ph in range(2):
            if (ph == 0) == fav_first:
                if not part_done and ((pos == 1 and fe >= ppx) or (pos == -1 and fe <= ppx)):
                    px = o[i] if ((pos == 1 and o[i] >= ppx) or (pos == -1 and o[i] <= ppx)) else ppx
                    pnl += ((px - entry) * pos - cost) * pf; size -= pf; part_done = True
                    ls = entry + pos * lockR * risk
                    if (pos == 1 and ls > stop) or (pos == -1 and ls < stop): stop = ls
                if tp > 0 and ((pos == 1 and fe >= tpx) or (pos == -1 and fe <= tpx)):
                    px = o[i] if ((pos == 1 and o[i] >= tpx) or (pos == -1 and o[i] <= tpx)) else tpx
                    pnl += ((px - entry) * pos - cost) * size; size = 0.0; closed = True; break
                f = (fe - entry) * pos / risk
                if f > mfe: mfe = f
            else:
                if (pos == 1 and ae <= stop) or (pos == -1 and ae >= stop):
                    pnl += ((stop - entry) * pos - cost) * size; closed = True; break
        if closed or size <= 1e-9: closed = True; break
        best = max(best, h[i]) if pos == 1 else min(best, l[i])
        prof = (best - entry) * pos
        if beR > 0 and prof >= beR * risk:
            ns = entry + pos * beL * risk
            if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        if ra > 0 and prof >= ra * risk:
            ns = entry + pos * rk * prof
            if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        if tkind == 1 and h4c[i]:
            ns = best - pos * tw
            if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        elif tkind == 2:
            ns = best - pos * tw
            if (pos == 1 and ns > stop) or (pos == -1 and ns < stop): stop = ns
        if lk < 0 and ((pos == 1 and stop >= entry) or (pos == -1 and stop <= entry)): lk = i
        if tsT > 0 and i - i0 == tsT and (c[i] - entry) * pos < tsR * risk:
            pnl += ((c[i] - entry) * pos - cost) * size; closed = True; break
        i += 1
    if not closed:
        j = min(i, n - 1); pnl += ((c[j] - entry) * pos - cost) * size; i = j
    return pnl / risk, i, mfe, lk
@njit(parallel=True, cache=True)
def sim_all(m, dirs, lvl, risk, tp, pf, pR, lockR, beR, beL, tkind, tw, ra, rk, tsT, tsR, hor, o, h, l, c, h4c, cost):
    K = len(m); R = np.empty(K, np.float32); X = np.empty(K, np.int64); MF = np.empty(K, np.float32); LK = np.empty(K, np.int64)
    for k in prange(K):
        r, x, mf, lk = sim_one(m[k], dirs[k], lvl[k], risk[k], tp[k], pf, pR[k], lockR, beR, beL, tkind, tw[k], ra[k], rk, tsT, tsR, hor[k], o, h, l, c, h4c, cost)
        R[k] = r; X[k] = x; MF[k] = mf; LK[k] = lk
    return R, X, MF, LK
# ---------------- policy grid
P = []
# TREND policies
for sq, tp, part, be, trail, rat, ts in itertools.product(
        ("k50", "k70", "k90"),
        ("none", "f50", "1R", "2R", "3R"),                    # full target: none, measured (f50/k), fixed R
        ("slot", "none", "half@f30"),                         # partial: slot's own (F1 at f-quantile + LOCK), none, half at f30 lock 0.1
        ("none", "be1"),                                      # breakeven: stop to +0.05R after 1R
        ("h4q80", "h4q50", "atr2", "atr4", "none"),           # trail: H4 measured (Assay), tighter H4, continuous 2/4 x TF-ATR, none
        ("none", "q90k50", "q70k50", "2R_k50"),               # ratchet: after measured/fixed profit keep 50%
        ("none", "ts_half")):                                 # time stop: after half the TF-horizon, exit if < 0
    P.append(dict(kind="trend", sq=sq, tp=tp, part=part, be=be, trail=trail, rat=rat, ts=ts))
# FADE policies
for sq, tp, be, rat, hm in itertools.product(("k50", "k70", "k90"), ("f30", "f50", "f70", "1R", "mean"), ("none", "be1"),
                                            ("none", "q70k50"), (0.5, 1.0, 2.0)):
    P.append(dict(kind="fade", sq=sq, tp=tp, be=be, rat=rat, hm=hm))
print("policies:", len(P), flush=True)
HOR_TF = {"3min": 720, "5min": 1440, "15min": 1440, "30min": 2880, "1h": 4320}
m = SIG.m1.values.astype(np.int64); dirs = SIG.dir.values.astype(np.int64); lvl = SIG.lvl.values; atr = SIG.atr.values; atr4 = SIG.atr4.values
ma20 = {}
for tf in SIG.tf.unique():
    G = R2.GR[tf]; mm = G.bars.close.rolling(20).mean().values; ma20[tf] = (G.pos, mm)
mean_dist = np.zeros(n)
for tf, (pos_, mm) in ma20.items():
    s = (SIG.tf == tf).values; bi = np.searchsorted(pos_, m[s]); mean_dist[s] = np.abs(mm[np.clip(bi, 0, len(mm) - 1)] - lvl[s])
def arrays(p, sel):
    k = np.clip(SIG[p["sq"]].values[sel], 0.3 if p["kind"] == "fade" else 0.5, 8.0); risk = k * atr[sel]
    def fq(col): return np.clip(SIG[col].values[sel] / k, 0.1, 5.0)
    tp = {"none": np.zeros(sel.sum()), "f50": fq("f50"), "f30": fq("f30"), "f70": fq("f70"), "1R": np.ones(sel.sum()), "2R": np.full(sel.sum(), 2.0),
          "3R": np.full(sel.sum(), 3.0), "mean": np.clip(mean_dist[sel] / risk, 0.1, 5.0)}[p["tp"]]
    pf, pR, lockR = 0.0, np.ones(sel.sum()), 0.0
    if p["kind"] == "trend":
        if p["part"] == "slot":
            f1 = SIG.f1.values[sel][0]; pR = np.clip(np.array([SIG[f"f{int(q*100)}"].values[i] for i, q in zip(np.where(sel)[0], SIG.qtp.values[sel])]) / k, 0.1, 3.0)
            pf = f1 if f1 > 0 else 1e-9; lockR = SIG.lock.values[sel][0]
        elif p["part"] == "half@f30": pf, pR, lockR = 0.5, fq("f30"), 0.1
        else: pf, pR = 0.0, np.full(sel.sum(), 99.0)
        tkind, tw = {"h4q80": (1, SIG.tw80.values[sel] * atr4[sel]), "h4q50": (1, SIG.tw50.values[sel] * atr4[sel]), "atr2": (2, 2 * atr[sel]),
                     "atr4": (2, 4 * atr[sel]), "none": (0, np.zeros(sel.sum()))}[p["trail"]]
        ra = {"none": np.zeros(sel.sum()), "q90k50": fq("f90"), "q70k50": fq("f70"), "2R_k50": np.full(sel.sum(), 2.0)}[p["rat"]]
        tsT = 0; hor = np.full(sel.sum(), 60 * 24 * 10)
        tsT = 1 if p["ts"] == "ts_half" else 0
        tsTv = np.array([HOR_TF[t] // 2 for t in SIG.tf.values[sel]]) if tsT else None
    else:
        tkind, tw = 0, np.zeros(sel.sum()); ra = fq("f70") if p["rat"] == "q70k50" else np.zeros(sel.sum())
        hor = (SIG.hor.values[sel] * p["hm"]).astype(np.int64); tsTv = None
    be = (1.0, 0.05) if p["be"] == "be1" else (0.0, 0.0)
    return risk, tp, pf, pR, lockR, be, tkind, tw, ra, hor, tsTv
R = np.full((n, len(P)), np.nan, np.float32); X = np.zeros((n, len(P)), np.int32); MF = np.full((n, len(P)), np.nan, np.float32); LK = np.full((n, len(P)), -1, np.int32)
import time; t0 = time.time()
for j, p in enumerate(P):
    sel = (SIG.kind == p["kind"]).values
    risk, tp, pf, pR, lockR, be, tkind, tw, ra, hor, tsTv = arrays(p, sel)
    if tsTv is not None:  # time stop differs per TF: run per TF group
        for tf in np.unique(SIG.tf.values[sel]):
            s2 = (SIG.tf.values[sel] == tf); idxs = np.where(sel)[0][s2]
            r, x, mf, lk = sim_all(m[idxs], dirs[idxs], lvl[idxs], risk[s2], tp[s2], pf, pR[s2], lockR, be[0], be[1], tkind, tw[s2], ra[s2], 0.5, HOR_TF[tf] // 2, 0.0, hor[s2], o, h, l, c, h4close, G_.COST_RT)
            R[idxs, j] = r; X[idxs, j] = x; MF[idxs, j] = mf; LK[idxs, j] = lk
    else:
        idxs = np.where(sel)[0]
        r, x, mf, lk = sim_all(m[idxs], dirs[idxs], lvl[idxs], risk, tp, pf, pR, lockR, be[0], be[1], tkind, tw, ra, 0.5, 0, 0.0, hor, o, h, l, c, h4close, G_.COST_RT)
        R[idxs, j] = r; X[idxs, j] = x; MF[idxs, j] = mf; LK[idxs, j] = lk
    if j % 100 == 0: print(j, round(time.time() - t0), "s", flush=True)
np.save("R.npy", R); np.save("X.npy", X); np.save("MF.npy", MF); np.save("LK.npy", LK)
json.dump(P, open("policies.json", "w"))
# index of the Assay baseline policy per kind
base_tr = [j for j, p in enumerate(P) if p == dict(kind="trend", sq="k70", tp="none", part="slot", be="none", trail="h4q80", rat="none", ts="none")]
print("done", round(time.time() - t0), "s; trend baseline policy index", base_tr)
