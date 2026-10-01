import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd
S=lab.SIG; rows=np.load("rows.npy"); Rs=np.load("Rs.npy"); Xs=np.load("Xs.npy")
t=lab.TIME[rows]; m25=np.asarray(t>=lab.D0); M1=S.m1.values[rows]
def greedy(R, X, take=None, pol=None):
    """R,X: per-row arrays (for chosen policy); returns idx (within rows) of taken trades, 2025+"""
    free=-1; out=[]
    for k in np.where(m25 if take is None else (m25&take))[0]:
        if M1[k]>free: out.append(k); free=X[k]
    return np.array(out,int)
def run(pol, take=None):
    pol=np.full(len(rows),pol) if np.isscalar(pol) else np.asarray(pol)
    R=Rs[np.arange(len(rows)),pol]; X=Xs[np.arange(len(rows)),pol]
    k=greedy(R,X,take); return k, R[k]
def met(pol,take=None):
    k,R=run(pol,take); return lab.metrics(R,t[k])
KEYS=["n","win","PF","sumR","avgR","maxDD_R","ret_dd","top5days_pct","months_pos","q_pos","weeks_pos_pct","eq_R2","ulcer_R"]
