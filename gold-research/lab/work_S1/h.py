import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd
lab._MS = np.load("ms.npy")
rows = np.load("rows.npy"); R1 = np.load("R1.npy"); X1 = np.load("X1.npy"); MF1=np.load("MF1.npy")
S = lab.SIG.iloc[rows].reset_index(drop=True); T = lab.TIME[rows]; M = S.m1.values
in25 = T >= lab.D0
P = lab.P; BASE = lab.baseline_policy("S1")
TREND = np.arange(3600)
def greedy(idx, xb):
    take = np.zeros(len(idx), bool); free = -1
    for k in range(len(idx)):
        if free < M[idx[k]]: take[k] = True; free = xb[k]
    return take
def run(pol=BASE, take=None):
    """pol: int or array len(rows); take: bool len(rows). returns local idx, R"""
    pol = np.full(len(rows), pol) if np.isscalar(pol) else np.asarray(pol)
    tm = in25.copy() if take is None else (in25 & take)
    idx = np.where(tm)[0]; r = R1[idx, pol[idx]]; x = X1[idx, pol[idx]]
    tk = greedy(idx, x); return idx[tk], r[tk]
def met(pol=BASE, take=None):
    i, r = run(pol, take); return lab.metrics(r, T[i])
K = ("n","win","PF","sumR","avgR","maxDD_R","ret_dd","months_pos","q_pos","weeks_pos_pct","eq_R2","ulcer_R","top5days_pct")
def fmt(m): return {k: m.get(k) for k in K}
def pname(j): p=P[j]; return "/".join(f"{p[k]}" for k in ("sq","tp","part","be","trail","rat","ts"))
