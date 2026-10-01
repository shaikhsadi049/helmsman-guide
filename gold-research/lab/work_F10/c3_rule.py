from common import *
import warnings; warnings.filterwarnings("ignore")
EX={"F10":109,"F11":73}
cols=list(F.columns)
fam={"all":cols,"mom":[c for c in cols if c[:3] in("m5_","m15","h1_") and any(k in c for k in["ret","rsi","z20","dist20","streak"])],
     "regime":[c for c in cols if any(k in c for k in ["atr_rank","er30","adx","stack","bbw_rank"])]+["day_rng_atr","hour"]}
def online_rule(rows,y,kn,feats,qcut=0.25,prior=20,thr=0.0,mintr=40):
    m=M1[rows]; skip=np.zeros(len(rows),bool); log=[]
    Xa=F[feats].values[rows]
    for a,b in zip(MS[:-1],MS[1:]):
        te=(m>=a)&(m<b)
        if not te.any(): continue
        tr=kn<a
        if tr.sum()<mintr: continue
        best=(1e9,None)
        for i,f in enumerate(feats):
            x=Xa[tr,i]; 
            for side in (0,1):
                c=np.nanquantile(x,qcut if side==0 else 1-qcut)
                sel=(x<=c) if side==0 else (x>=c)
                n=sel.sum(); sm=y[tr][sel].sum()/(n+prior)
                if sm<best[0]: best=(sm,(i,side,c))
        if best[0]<thr:
            i,side,c=best[1]; x=Xa[te,i]; skip[np.where(te)[0]]=(x<=c) if side==0 else (x>=c); log.append((str(T[rows][te][0].to_period('M')),feats[i],"low" if side==0 else "high",round(best[0],3)))
    return skip,log
for s in ["F10","F11"]:
    for pool in ["own","pooled"]:
        sl=[s] if pool=="own" else ["F8","F9","F10","F11"]
        rows=np.where(S.slot.isin(sl).values)[0]; rows=rows[np.argsort(M1[rows],kind="stable")]
        y=RF[li_(rows),EX[s]]; kn=XF[li_(rows),EX[s]]; tgt=(S.slot.values[rows]==s)&(T[rows]>=lab.D0)
        for fn,fs in fam.items():
            for qc in [0.2,0.33]:
                sk,log=online_rule(rows,y,kn,fs,qcut=qc)
                rr,R=sim(rows[tgt],EX[s],~sk[tgt]); m=short(met(rr,R))
                print(s,pool,fn,qc,"skipped",sk[tgt].sum(),m)
                if fn!="all" and qc==0.2: print("   ",log[::3])
