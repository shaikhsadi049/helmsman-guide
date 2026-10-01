import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import v3_parity as V, dyn2_run as R2, adv3 as D, adv4, adv6, gcdata as G_, mr as M
idx = R2.idx
PRE = []
for si, sl in enumerate(V.SLOTS[:6]):
    tf, fam, nc, sess, qsl, qtp, lock, qtr, f1 = sl
    E = V.entries_ea(tf, fam, nc, sess); G = R2.GR[tf]; m = E["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, qsl, 2.0), 0.5, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, qtp, 1.0) / k, 0.1, 3.0); tw = R2.trail_q(m, qtr) * E["atr4"]
    PRE.append((si, m, E, k, risk, r1, tw, G, f1, lock))
def build(q=None, f=0.5):
    rows = []
    for si, m, E, k, risk, r1, tw, G, f1, lock in PRE:
        args = (m, E["dir"].astype(np.int64), E["lvl"], risk, r1, tw)
        tail = (G.o, G.h, G.l, G.c, R2.G4.mgmt, R2.G4.trend_up, R2.G4.trend_dn, f1 if f1 > 0 else 1e-9, lock, False, G_.COST_RT, 60 * 24 * 30)
        if q is None: res = adv4.sim_dyn2(*args, *tail)
        else:
            A = D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, q, 99.0) / k   # market-measured "big profit" in R
            res = adv6.sim_rat(*args, A, f, *tail)
        live = np.where(idx[m] >= R2.S25)[0]
        for j in live:
            rows.append((si, int(m[j]) + 1, int(res[j, 2]), int(res[j, 4]) if res[j, 4] >= 0 else 10**12, res[j, 0], risk[j], idx[m[j]], res[j, 1]))
    T = pd.DataFrame(rows, columns=["slot", "t_in", "t_out", "t_lock", "R", "risk", "time", "mfe"]).sort_values("t_in").reset_index(drop=True)
    T["d_trend"] = M.dt_at(T.t_in.values - 1); T["kind"] = "trend"
    return T
def giveback_stats(T):
    keep = np.zeros(len(T), bool); bu = {}
    for i, (s, a, b) in enumerate(zip(T.slot, T.t_in, T.t_out)):
        if bu.get(s, -1) < a: keep[i] = True; bu[s] = b
    X = T[keep]; big = X.mfe >= 2
    return f"trades {len(X)} | reached >=2R: {big.sum()} of which ended <0.5R: {(big & (X.R < 0.5)).sum()} | sumR {X.R.sum():+.0f} | win {(X.R>0).mean()*100:.0f}%"
import pickle
out = {}
for q, f in [(None, 0), (0.8, 0.5), (0.9, 0.5), (0.9, 0.7), (0.95, 0.5), (0.95, 0.7), (0.8, 0.3)]:
    T = build(q, f); out[(q, f)] = T
    print(f"ratchet q={q} f={f}: " + giveback_stats(T), flush=True)
pickle.dump(out, open("../ratchet_T.pkl", "wb"))
