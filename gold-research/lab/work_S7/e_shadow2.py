from common import *
import pickle
ms=np.load("ms.npy"); F=F7()
def stream(j):
    Xv=X7[:,j]; Rv=R7[:,j]; out=[]; free=-1
    for i in range(len(rows)):
        if free<M[i]: out.append(i); free=Xv[i]
    out=np.array(out); return M[out], Xv[out], Rv[out].astype(float)
fam24=[pidx(sq=s,tp="none",part="none",be=be,trail="h4q80",rat=r,ts="none")[0] for s in ("k50","k70","k90") for r in ("none","q90k50","q70k50","2R_k50") for be in ("none","be1")]
small12=[pidx(sq=s,tp="none",part=p,be="none",trail="h4q80",rat=r,ts="none")[0] for s in ("k50","k70") for p in ("slot","none") for r in ("none","q90k50","2R_k50")]
S={j:stream(j) for j in set(fam24+small12)}
def sc(j,a,obj,win):
    m0,x,r=S[j]; k=(x<a)&((m0>=a-win) if win else True)
    if k.sum()<10: return -np.inf
    r=r[k]; eq=np.cumsum(r); dd=np.maximum.accumulate(np.r_[0,eq])[1:]-eq
    if obj=="retdd": return eq[-1]/max(dd.max(),2)
    if obj=="ret_ulcer": return eq[-1]/max(np.sqrt((dd**2).mean()),1)
def sel(cs,obj,win):
    ch=np.full(len(rows),cs[0]); log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=(M>=a)&(M<b); best=cs[int(np.argmax([sc(j,a,obj,win) for j in cs]))]; ch[te]=best; log.append(pname(best))
    return ch,log
def adx_take(chpol,qq=0.8,f="h1_adx"):
    x=F[f].values; take=np.ones(len(rows),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        te=(M>=a)&(M<b); tr=M<a  # thresholds only need past feature values (no outcome needed)
        take[te]=~(x[te]>np.nanquantile(x[tr],qq))
    return take
TK=adx_take(None)
res={}; WIN_6M=6*30*1440; WIN_9M=9*30*1440
for fn,cs in (("small12",small12),("fam24",fam24)):
    for obj in ("retdd","ret_ulcer"):
        for wn,win in (("exp",None),("9m",WIN_9M)):
            ch,log=sel(cs,obj,win); key=f"{fn}|{obj}|{wn}"; res[key]=(ch,log)
            m=met(ch); mf=met(ch,TK)
            print(f"{key:26s} nofilt",{k:m[k] for k in ("n","PF","sumR","maxDD_R","months_pos","eq_R2","ulcer_R","top5days_pct")})
            print(f"{'':26s} +adx  ",{k:mf[k] for k in ("n","PF","sumR","maxDD_R","months_pos","eq_R2","ulcer_R","top5days_pct")})
            print(f"{'':26s} picks:",pd.Series(log).value_counts().head(4).to_dict())
pickle.dump(dict(res=res,TK=TK),open("shadow2.pkl","wb"))
