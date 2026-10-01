import sys; L="/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab"; sys.path.insert(0,L); import lab, numpy as np, pandas as pd
S=lab.SIG; rows=np.load(L+"/work_S4/rows.npy"); R4=np.load(L+"/work_S4/R4.npy"); X4=np.load(L+"/work_S4/X4.npy")
T=lab.TIME[rows]; m1=S.m1.values[rows]; IN=np.asarray(T>=lab.D0); P=lab.P; BASE=lab.baseline_policy("S4")
Q=np.asarray(T.tz_localize(None).to_period("Q").astype(str))
def greedy_local(pol, take=None):
    """pol: array per local row or int; returns idx of taken (2025+), R"""
    pol=np.full(len(rows),pol) if np.isscalar(pol) else np.asarray(pol)
    take=np.ones(len(rows),bool) if take is None else np.asarray(take)
    idx=np.where(IN&take)[0]; Rv=R4[idx,pol[idx]]; Xv=X4[idx,pol[idx]]
    keep=[]; free=-1
    for k,i in enumerate(idx):
        if free<m1[i]: keep.append(k); free=Xv[k]
    keep=np.array(keep,int); return idx[keep], Rv[keep]
def M(pol, take=None):
    i,r=greedy_local(pol,take); return lab.metrics(r,T[i])
def pstr(j): p=P[j]; return f"{p['sq']}/{p['tp']}/{p['part']}/{p['be']}/{p['trail']}/{p['rat']}/{p['ts']}"
K=("n","win","PF","sumR","maxDD_R","months_pos","q_pos","weeks_pos_pct","eq_R2","ulcer_R","top5days_pct")
def short(m): return {k:m[k] for k in K}
