import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import v3_parity as V, dyn2_run as R2, adv3 as D, adv4, adv5, gcdata as G_
from numba import njit
idx = R2.idx
@njit(cache=True)
def known_hit_quantile(m, hit_at, look, q):
    K = len(m); out = np.full(K, -1.0); buf = np.empty(look)
    for k in range(K):
        c = 0; j = k - 1
        while j >= 0 and c < look:
            if hit_at[j] >= 0 and hit_at[j] <= m[k]: buf[c] = hit_at[j] - m[j]; c += 1
            j -= 1
        if c >= 20: out[k] = np.quantile(buf[:c], q)
    return out
PRE = []
for si, sl in enumerate(V.SLOTS):
    tf, fam, nc, sess, qsl, qtp, lock, qtr, f1 = sl
    E = V.entries_ea(tf, fam, nc, sess); G = R2.GR[tf]; m = E["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, qsl, 2.0), 0.5, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, qtp, 1.0) / k, 0.1, 3.0); tw = R2.trail_q(m, qtr) * E["atr4"]
    args = (m, E["dir"].astype(np.int64), E["lvl"], risk, r1, tw)
    tail = (G.o, G.h, G.l, G.c, R2.G4.mgmt, R2.G4.trend_up, R2.G4.trend_dn, f1 if f1 > 0 else 1e-9, lock, False, G_.COST_RT, 60 * 24 * 30)
    base = adv4.sim_dyn2(*args, *tail)
    PRE.append((si, m, args, tail, base, risk))
def portfolio(q, fac):
    rows = []
    for si, m, args, tail, base, risk in PRE:
        if q is None: res = base
        else:
            ts = known_hit_quantile(m, base[:, 4].astype(np.int64), 60, q) * fac
            res = adv5.sim_dyn3(*args, ts, *tail)
        for j in np.where(idx[m] >= R2.S25)[0]:
            rows.append((si, int(m[j]) + 1, int(res[j, 2]), int(res[j, 4]) if res[j, 4] >= 0 else 10**12, res[j, 0], risk[j]))
    T = pd.DataFrame(rows, columns=["slot", "t_in", "t_out", "t_lock", "R", "risk"]).sort_values("t_in").reset_index(drop=True)
    keep = np.zeros(len(T), bool); bu = {}
    for i, (s, a, b) in enumerate(zip(T.slot, T.t_in, T.t_out)):
        if bu.get(s, -1) < a: keep[i] = True; bu[s] = b
    return T, keep
def summ(T, keep, R):
    R = R[keep]; w = R > 0; tm = pd.Series(idx[T.t_in.values[keep]]).dt.tz_localize(None).dt.to_period("M")
    mo = pd.Series(R).groupby(tm.values).sum()
    return f"n {len(R)} win {w.mean()*100:3.0f}% PF {R[w].sum()/-R[~w].sum():4.2f} sumR {R.sum():+6.1f} | flat months(neg) {(mo<0).sum()}/{len(mo)} worst month {mo.min():+.1f}R"
import pickle
out = {}
for q, fac in [(None, 0), (0.8, 1.0), (0.8, 1.5), (0.8, 2.0), (0.9, 1.0), (0.9, 1.5), (0.9, 2.0), (0.95, 1.5), (0.95, 2.0)]:
    T, keep = portfolio(q, fac); R0 = T.R.values; Rw = np.where(R0 > 0, R0 * .5, R0); Rc = R0 - 1.66 / T.risk.values
    print(f"tstop q={q} x{fac}: normal {summ(T, keep, R0)} || weak sumR {Rw[keep].sum():+6.1f} | cost$2 sumR {Rc[keep].sum():+6.1f}")
    out[(q, fac)] = T
pickle.dump(out, open("../tstop_T.pkl", "wb"))
