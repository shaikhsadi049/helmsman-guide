from h import *
ms=lab._MS
def col(c):
    if isinstance(c,tuple): a,b,w=c; return w*R1[:,a]+(1-w)*R1[:,b], np.maximum(X1[:,a],X1[:,b])
    return R1[:,c], X1[:,c]
def online(cands, crit):
    Rm=np.stack([col(c)[0] for c in cands],1); Xm=np.stack([col(c)[1] for c in cands],1); kn=Xm.max(1)
    ch=np.zeros(len(rows),int)
    for a,b in zip(ms[:-1],ms[1:]):
        te=(M>=a)&(M<b); tr=kn<a
        if not te.any() or tr.sum()<30: continue
        x=Rm[tr]
        if crit=="mean": s=x.mean(0)
        elif crit=="sharpe": s=x.mean(0)/x.std(0)
        elif crit=="median": s=np.median(x,0)
        elif crit=="mean_minus_sd": s=x.mean(0)-0.25*x.std(0)
        ch[te]=np.argmax(s)
    r=Rm[np.arange(len(rows)),ch]; x=Xm[np.arange(len(rows)),ch]
    idx=np.where(in25)[0]; tk=greedy(idx,x[idx]); ii=idx[tk]
    return lab.metrics(r[ii],T[ii]), pd.Series(ch[in25]).value_counts().to_dict()
C=[1200,1248,1254,1320,(1200,1320,0.5),(1248,1320,0.5),1324]
for crit in ("mean","sharpe","median","mean_minus_sd"):
    m,u=online(C,crit); print(crit, fmt(m), u)
for crit in ("mean","sharpe"):
    m,u=online([1200,(1200,1320,0.5),1320],crit); print("3cand",crit, fmt(m), u)
