import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd, time
S=lab.SIG; R_=lab.load_R(); F=lab.load_F(); N=len(S)
ms=lab._ms(); M1=S.m1.values
r6=np.where(S.slot.values=="S6")[0]; r3=np.where(S.slot.values=="S3")[0]
base=lab.baseline_policy("S6")
C=[base,2360,2320,2280,2282,3560,2080,2120,1086,2286,1328,88,2488,1288,3520,2044]
def show(name,choice=None,take=None):
    m,rr,R=lab.evaluate("S6",choice,take)
    print(f"{name:40s}",{k:m[k] for k in ("n","PF","sumR","maxDD_R","months_pos","q_pos","top5days_pct","eq_R2","ulcer_R")}); return m
show("baseline")
for j in [2360,2320,2280,3560,2080]: show(f"fixed {j} IS",j)
def chooser(train_rows, test_rows, cands, crit, regime=None, nb=3, prior=20):
    Rm=np.stack([np.asarray(R_[train_rows,j]) for j in cands],1).astype(float)
    known=lab.known_bar(train_rows,cands)
    choice=np.full(N,base); log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=test_rows[(M1[test_rows]>=a)&(M1[test_rows]<b)]
        if len(te)==0: continue
        tr=known<a
        if tr.sum()<30: continue
        def sc(X):
            if crit=="mean": return np.nanmean(X,0)
            if crit=="sharpe": return np.nanmean(X,0)/np.nanstd(X,0)
            if crit=="clip3": return np.nanmean(np.minimum(X,3),0)
            if crit=="clip2": return np.nanmean(np.minimum(X,2),0)
            if crit=="median": return np.nanmedian(X,0)
        if regime is None:
            c=cands[int(np.argmax(sc(Rm[tr])))]; choice[te]=c; log.append(c); continue
        g=regime[train_rows][tr]; edges=np.nanquantile(g,np.linspace(0,1,nb+1)[1:-1])
        btr=np.searchsorted(edges,g); bte=np.searchsorted(edges,regime[te]); allsc=sc(Rm[tr])
        best=[]
        for k in range(nb):
            sel=btr==k; s=(sc(Rm[tr][sel])*sel.sum()+prior*allsc)/(sel.sum()+prior) if sel.sum()>5 else allsc
            best.append(cands[int(np.argmax(s))])
        choice[te]=np.array(best)[bte]; log.append(tuple(best))
    return choice,log
out={}
for pool in ["S6","S6+S3"]:
    trr=r6 if pool=="S6" else np.r_[r6,r3]
    for crit in ["mean","sharpe","clip3","clip2","median"]:
        ch,log=chooser(trr,r6,C,crit)
        m=show(f"causal {pool} {crit}",ch)
        print("    picks:",pd.Series(log).value_counts().to_dict())
for feat in ["h4_er30","h4_adx","d1_atr_rank","h4_atr_rank","h1_er30","day_rng_atr","d1_er30","h4_bbw_rank","hour"]:
    reg=F[feat].values
    for crit in ["clip3","sharpe"]:
        ch,log=chooser(np.r_[r6,r3],r6,C,crit,regime=reg)
        show(f"regime {feat} {crit}",ch)
