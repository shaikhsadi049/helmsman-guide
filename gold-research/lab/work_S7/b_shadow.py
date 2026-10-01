from common import *
import pickle
ms=np.load("ms.npy")
# greedy stream per candidate over ALL rows (warm-up incl.)
def stream(j):
    Xv=X7[:,j]; Rv=R7[:,j]; out=[]; free=-1
    for i in range(len(rows)):
        if free<M[i]: out.append(i); free=Xv[i]
    out=np.array(out); return out, Xv[out], Rv[out].astype(float)
cands=list(range(3600))
S={j:stream(j) for j in cands}
def score_at(j,a,obj):
    i,x,r=S[j]; k=x<a
    if k.sum()<15: return -np.inf
    r=r[k]; eq=np.cumsum(r); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
    if obj=="sum": return eq[-1]
    if obj=="retdd": return eq[-1]/max(dd,2)
    if obj=="retdd_r2":
        x_=np.arange(len(eq)); r2=np.corrcoef(x_,eq)[0,1]**2 if eq.std()>0 else 0
        return eq[-1]/max(dd,2)*r2*np.sign(eq[-1])
def online_sel(cs,obj,window=None):
    ch=np.full(len(rows),cs[0]); log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=(M>=a)&(M<b)
        sc=[score_at(j,a,obj) for j in cs]; best=cs[int(np.argmax(sc))]
        ch[te]=best; log.append(pname(best))
    return ch,log
small=[pidx(sq=s,tp="none",part=p,be="none",trail="h4q80",rat=r,ts="none")[0] for s in ("k50","k70") for p in ("slot","none") for r in ("none","q90k50","2R_k50")]
out={}
for nm,cs in [("all3600",cands),("small12",small)]:
    for obj in ("sum","retdd","retdd_r2"):
        ch,log=online_sel(cs,obj); out[f"{nm}|{obj}"]=(ch,log)
        print(f"{nm}|{obj:9s}",short(met(ch)))
        print("   picks:", " ".join(sorted(set(log))[:6]), "| first/last:", log[0], log[-1])
pickle.dump(out,open("shadow.pkl","wb"))
