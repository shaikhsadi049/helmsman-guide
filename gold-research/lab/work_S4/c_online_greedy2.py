from common import *
ms=lab._ms(); F=lab.load_F(); h4=F.h4_stack.values[rows]
key={}
for j in range(3600): key.setdefault(hash(R4[:,j].tobytes()+X4[:,j].tobytes()),j)
U=np.array(sorted(key.values()))
Mo=np.asarray(T.tz_localize(None).to_period("M").astype(str))
def gsim(j, upto):
    idx=np.where(X4[:,j]<upto)[0]; free=-1; out=[]
    for i in idx:
        if free<m1[i]: out.append(i); free=X4[i,j]
    return np.array(out,int)
def score(ii,j,crit):
    r=R4[ii,j]
    if len(r)<10: return -1e9
    eq=np.cumsum(r)
    if crit=="sumR2":
        r2=np.corrcoef(np.arange(len(eq)),eq)[0,1]**2 if eq.std()>0 else 0; return eq[-1]*r2 if eq[-1]>0 else eq[-1]
    if crit=="mposfrac_sum":
        mo=pd.Series(r).groupby(Mo[ii]).sum(); return (mo>0).mean()*max(eq[-1],0)
    if crit=="sum_over_ulcer":
        u=np.sqrt(np.mean((np.maximum.accumulate(np.r_[0,eq])[1:]-eq)**2)); return eq[-1]/(u+0.2)
    if crit=="sum_month_sd":
        mo=pd.Series(r).groupby(Mo[ii]).sum(); return mo.mean()/(mo.std()+0.5)
cache={}
for crit in ["sumR2","mposfrac_sum","sum_over_ulcer","sum_month_sd"]:
    ch=np.full(len(rows),BASE); log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m1>=a)&(m1<b)
        if not te.any(): continue
        best=-1e18; bj=BASE
        for j in U:
            if (j,a) not in cache: cache[(j,a)]=gsim(j,a)
            s=score(cache[(j,a)],j,crit)
            if s>best: best=s; bj=j
        ch[te]=bj; log.append(pstr(bj))
    np.save(f"ch_{crit}.npy",ch)
    take=h4==1
    print(crit,short(M(ch)),"\n  +h4stack",short(M(ch,take)),"\n  ",log[::3],flush=True)
