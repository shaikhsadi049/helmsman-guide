from common import *
import numba
@numba.njit
def gfull(m1,x):
    tk=np.zeros(len(m1),np.bool_); free=-1
    for k in range(len(m1)):
        if free<m1[k]: tk[k]=True; free=x[k]
    return tk
# month index of each exit bar
allms=np.r_[np.searchsorted(MS, MS[0]) ,0]  # dummy
# monthly buckets from 2024-06: use calendar month of signal time
mon=np.asarray(T.tz_localize(None).to_period("M").astype(str)); um=sorted(set(mon)); mid=np.array([um.index(v) for v in mon])
NP=3600; MR=np.zeros((NP,len(um))); TK=np.zeros((NP,len(ROWS)),bool)
for j in range(NP):
    tk=gfull(M1,XX[:,j].astype(np.int64)); TK[j]=tk
    np.add.at(MR[j], mid[tk], RR[tk,j])
np.save("TK.npy",TK)
# causal: at month a (calendar index of 2025-01 + i), use completed trades: x<a. approximate monthly R with trades exited before a, binned by entry month
first=um.index("2025-01")
def scores(a, kind, look=12):
    out=np.zeros(NP)
    for j in range(NP):
        tk=TK[j]&(XX[:,j]<a)
        mr=np.bincount(mid[tk],weights=RR[tk,j],minlength=len(um))
        cur=np.searchsorted(MS,a)+first   # current month index
        w=mr[max(0,cur-look):cur]
        if kind=="msharpe": out[j]=w.mean()/(w.std()+0.5)
        elif kind=="mpos": out[j]=(w>0).mean()+0.01*w.mean()
        elif kind=="sum_ulcer":
            eq=np.cumsum(RR[tk,j]); u=np.sqrt(np.mean((np.maximum.accumulate(np.r_[0,eq])[1:]-eq)**2)) if len(eq) else 9
            out[j]=eq[-1]/(u+1) if len(eq) else -9
    return out
for kind in ["msharpe","mpos","sum_ulcer"]:
  for look in ([6,12] if kind!="sum_ulcer" else [0]):
    ch=np.full(len(ROWS),BASE); picks=[]
    for a,b in zip(MS[:-1],MS[1:]):
        te=(M1>=a)&(M1<b); j=int(np.argmax(scores(a,kind,look))); ch[te]=j; picks.append(j)
    i,r=run(ch); print(kind,look,short(met(i,r))); print("   picks",picks)
