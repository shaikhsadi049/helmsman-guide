from common import *
ms=lab._ms()
# dedupe policies with identical R and X columns over S4
key={}
for j in range(3600):
    h=hash(R4[:,j].tobytes()+X4[:,j].tobytes()); key.setdefault(h,j)
U=np.array(sorted(key.values())); print("distinct", len(U))
def gsim(j, upto):
    """greedy over all S4 signals whose exit < upto (resolved), returns R seq and exit times"""
    idx=np.where(X4[:,j]<upto)[0]; free=-1; out=[]
    for i in idx:
        if free<m1[i]: out.append(i); free=X4[i,j]
    return np.array(out,int)
def score(r, crit, t=None):
    if len(r)<10: return -1e9
    eq=np.cumsum(r); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
    if crit=="sum": return eq[-1]
    if crit=="sum_dd": return eq[-1]/(dd+1)
    if crit=="sum_dd2": return eq[-1]/(dd+2)**2
    if crit=="ulcer":
        u=np.sqrt(np.mean((np.maximum.accumulate(np.r_[0,eq])[1:]-eq)**2)); return eq[-1]/(u+0.5)
cache={}
res=[];logs={}
for crit in ["sum","sum_dd","sum_dd2","ulcer"]:
  for lb_days in [None, 180]:
    ch=np.full(len(rows),BASE); log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m1>=a)&(m1<b)
        if not te.any(): continue
        best=-1e18; bj=BASE
        for j in U:
            k=(j,a)
            if k not in cache: cache[k]=gsim(j,a)
            ii=cache[k]
            if lb_days: ii=ii[T[ii]>=pd.Timestamp(lab.MONTHS[np.searchsorted(ms,a)])-pd.Timedelta(days=lb_days)]
            s=score(R4[ii,j],crit)
            if s>best: best=s; bj=j
        ch[te]=bj; log.append(pstr(bj))
    m=M(ch); res.append(dict(crit=crit,lb=lb_days,**short(m))); logs[(crit,lb_days)]=log
    print(crit,lb_days,short(m),flush=True); print("   ",log[::2])
pd.DataFrame(res).to_pickle("online_greedy.pkl")
