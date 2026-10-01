from common import *
import numba
@numba.njit
def gsim(m1, x, r, a):
    free=-1; s=0.0; pk=0.0; dd=0.0; n=0
    for k in range(len(m1)):
        if m1[k]>=a: break
        if free<m1[k] and x[k]<a:
            free=x[k]; s+=r[k]; n+=1
            if s>pk: pk=s
            if pk-s>dd: dd=pk-s
    return s,dd,n
cands=np.arange(3600)
res={}
SC=np.zeros((len(MS)-1,3600,3))
for mi,(a,b) in enumerate(zip(MS[:-1],MS[1:])):
    for j in cands:
        SC[mi,j]=gsim(M1, XX[:,j].astype(np.int64), RR[:,j].astype(np.float64), a)
np.save("sc_greedy.npy",SC)
def pick(score):
    ch=np.full(len(ROWS),BASE)
    for mi,(a,b) in enumerate(zip(MS[:-1],MS[1:])):
        te=(M1>=a)&(M1<b); ch[te]=int(np.argmax(score(mi)))
    return ch
objs={"g_sum":lambda mi:SC[mi,:,0],"g_sum/dd":lambda mi:SC[mi,:,0]/(SC[mi,:,1]+2),"g_sum-dd":lambda mi:SC[mi,:,0]-2*SC[mi,:,1]}
# per-signal mean using per-policy known
def pick_mean(kind):
    ch=np.full(len(ROWS),BASE)
    for a,b in zip(MS[:-1],MS[1:]):
        te=(M1>=a)&(M1<b); kn=XX[:,:3600]<a
        Rm=np.where(kn,RR[:,:3600],np.nan)
        if kind=="mean": s=np.nanmean(Rm,0)
        else:
            H=np.where(kn,(XX[:,:3600]-M1[:,None]).astype(float),np.nan); s=np.nansum(Rm,0)/np.nansum(H,0)
        ch[te]=int(np.nanargmax(s))
    return ch
chs={k:pick(f) for k,f in objs.items()}; chs["sig_mean"]=pick_mean("mean"); chs["sig_rate"]=pick_mean("rate")
for k,ch in chs.items():
    i,r=run(ch); print(k, short(met(i,r)))
    ms=[int(ch[(M1>=a)&(M1<b)][0]) if ((M1>=a)&(M1<b)).any() else -1 for a,b in zip(MS[:-1],MS[1:])]
    print("   monthly picks:", ms)
np.save("chs.npy",np.stack([chs[k] for k in chs])); print(list(chs))
