from common import *
import itertools
ms=lab._ms(); MON=lab.MONTHS
def gsim(R,X,ok):
    free=-1; out=[]
    for k in np.where(ok)[0]:
        if M1[k]>free: out.append(R[k]); free=X[k]
    return np.array(out)
def rdd(r):
    if len(r)==0: return -9
    eq=np.cumsum(r); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max(); return r.sum()/max(dd,1.0)
def online_blend(cands, topk=8, kind="retdd", window=None):
    Rc=np.zeros(len(rows)); Xc=np.zeros(len(rows),dtype=np.int64); log=[]
    for a,b,mo in zip(ms[:-1],ms[1:],MON[:-1]):
        test=(M1>=a)&(M1<b)
        if not test.any(): continue
        lo=0 if window is None else a-window*30*1440
        sc={}
        for j in cands:
            r=gsim(Rs[:,j],Xs[:,j],(Xs[:,j]<a)&(M1>=lo)); sc[(j,)]=rdd(r) if kind=="retdd" else r.sum()
        top=[c[0] for c in sorted(sc,key=sc.get,reverse=True)[:topk]]
        for i,j in itertools.combinations(top,2):
            R=0.5*(Rs[:,i]+Rs[:,j]); X=np.maximum(Xs[:,i],Xs[:,j]); r=gsim(R,X,(X<a)&(M1>=lo)); sc[(i,j)]=rdd(r) if kind=="retdd" else r.sum()
        best=max(sc,key=sc.get); log.append(best)
        Rc[test]=np.mean([Rs[test,j] for j in best],0); Xc[test]=np.max([Xs[test,j] for j in best],0)
    return Rc,Xc,log
k50=lab.policy_index(kind="trend",sq="k50",trail="h4q80")
for kind in ["retdd","sum"]:
  for win in [None,12]:
    Rc,Xc,log=online_blend(k50,8,kind,win); k=greedy(Rc,Xc); m=lab.metrics(Rc[k],t[k]); print("blend-online",kind,win,{x:m[x] for x in KEYS}); print("   ",log)
    np.save(f"blend_{kind}_{win}_R.npy",Rc); np.save(f"blend_{kind}_{win}_X.npy",Xc)
