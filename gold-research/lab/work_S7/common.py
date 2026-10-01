import sys; sys.path.insert(0,".."); import lab, numpy as np, pandas as pd
rows=np.load("rows7.npy"); R7=np.load("R7.npy"); X7=np.load("X7.npy")
T=lab.TIME[rows]; M=lab.SIG.m1.values[rows]; IN=np.asarray(T>=lab.D0)
P=lab.P; BASE=lab.baseline_policy("S7")
def run(pol, take=None):
    """pol: int or array over S7 rows (local); take: bool over local rows. returns local idx taken, R"""
    pol=np.full(len(rows),pol) if np.isscalar(pol) else np.asarray(pol)
    tk=IN.copy() if take is None else (IN & np.asarray(take))
    idx=np.where(tk)[0]; Rv=R7[idx,pol[idx]]; Xv=X7[idx,pol[idx]]
    out=[]; free=-1
    for k,i in enumerate(idx):
        if free<M[i]: out.append(k); free=Xv[k]
    out=np.array(out,int); return idx[out], Rv[out].astype(float)
def met(pol,take=None):
    i,R=run(pol,take); return lab.metrics(R,T[i])
def score(m):  # smoothness score used for ranking
    return m["sumR"]/max(m["maxDD_R"],1)*m["eq_R2"]
KEYS=("n","win","PF","sumR","maxDD_R","months_pos","q_pos","weeks_pos_pct","eq_R2","ulcer_R","top5days_pct")
def short(m): return {k:m[k] for k in KEYS}
def pname(j):
    p=P[j]; return "/".join(str(p[k]) for k in ("sq","tp","part","be","trail","rat","ts"))
lab._MS=np.load("ms.npy")
def F7():
    return lab.load_F().iloc[rows].reset_index(drop=True)
def pidx(**kw):
    return lab.policy_index(kind="trend",**kw)
def to_full(local):  # local array over S7 rows -> full length array for lab functions
    out=np.zeros(len(lab.SIG),dtype=np.asarray(local).dtype); out[rows]=local; return out
def monthly(pol,take=None):
    i,R=run(pol,take); return pd.Series(R,index=T[i].tz_localize(None).to_period("M")).groupby(level=0).sum()
