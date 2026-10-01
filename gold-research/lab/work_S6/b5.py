import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd
S=lab.SIG; R_=lab.load_R(); X_=lab.load_X(); N=len(S); ms=lab._ms(); M1=S.m1.values
r6=np.where(S.slot.values=="S6")[0]; r3=np.where(S.slot.values=="S3")[0]; base=lab.baseline_policy("S6")
G=pd.read_pickle("greedy_all.pkl"); C=list(G.drop_duplicates(subset=["n","sumR","maxDD_R","PF"]).index)  # dedup by S6 2025 behaviour (approx)
C=list(range(3600))
for pool in ["S6","S6+S3"]:
    trr=r6 if pool=="S6" else np.r_[r6,r3]
    Rm=np.asarray(R_[trr,:3600]).astype(float); known=np.asarray(X_[trr,:3600]).max(1)
    for crit in ["clip3","sharpe","median","mean"]:
        choice=np.full(N,base); picks=[]
        for a,b in zip(ms[:-1],ms[1:]):
            te=r6[(M1[r6]>=a)&(M1[r6]<b)]; tr=known<a
            if len(te)==0 or tr.sum()<30: continue
            X=Rm[tr]
            s={"clip3":np.nanmean(np.minimum(X,3),0),"sharpe":np.nanmean(X,0)/np.nanstd(X,0),"median":np.nanmedian(X,0),"mean":np.nanmean(X,0)}[crit]
            c=int(np.nanargmax(s)); choice[te]=c; picks.append(c)
        m,rr,R=lab.evaluate("S6",choice)
        print(pool,crit,{k:m[k] for k in ("n","PF","sumR","maxDD_R","months_pos","q_pos","top5days_pct","eq_R2","ulcer_R")})
        print("   picks",{f"{k}:{lab.P[k]['sq']}/{lab.P[k]['tp']}/{lab.P[k]['part']}/{lab.P[k]['be']}/{lab.P[k]['trail']}/{lab.P[k]['rat']}/{lab.P[k]['ts']}":v for k,v in pd.Series(picks).value_counts().items()})
