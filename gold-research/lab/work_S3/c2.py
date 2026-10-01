from common import *
import time
Fall=lab.load_F(); S=lab.SIG
R_=lab.load_R(); X_=lab.load_X()
res=[]
def evalskip(skip,label):
    take=~skip; i,r=run(BASEPOL,take); m=short(met(i,r)); m["label"]=label; m["skipped_sig%"]=round(skip[IN25].mean()*100,1); res.append(m); print(m,flush=True)
for BASEPOL in [2168,1208]:
    y3=RR[:,BASEPOL]; kn3=XX[:,BASEPOL]
    i,r=run(BASEPOL); print("NOFILTER",BASEPOL,short(met(i,r)))
    # S3 only, regression
    t0=time.time()
    p=lab.online_predict(np.arange(len(ROWS)) if False else ROWS, y3, Fall.iloc[ROWS], kn3)
    print("t",time.time()-t0)
    v=IN25&~np.isnan(p); print("IC S3-only", np.corrcoef(p[v],y3[v])[0,1])
    evalskip(p<0, f"{BASEPOL} ML S3 reg pred<0")
    # classification
    prm=dict(objective="binary", learning_rate=0.03, num_leaves=8, min_data_in_leaf=25, feature_fraction=0.5, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0, verbose=-1, num_threads=1, seed=7)
    pc=lab.online_predict(ROWS,(y3>0).astype(float),Fall.iloc[ROWS],kn3,params=prm)
    for th in [0.5,0.6]:
        evalskip(pc<th*0+np.nanmean(y3[IN25]>0)*th/0.5*0 + th if False else pc< (1-th), f"{BASEPOL} ML S3 clf P(win)<{1-th:.1f}")
    # pooled trend slots
    pr=np.where(S.kind.values=="trend")[0]
    Xp=Fall.iloc[pr].copy()
    for s in ["S1","S2","S3","S4","S5","S6","S7"]: Xp["is_"+s]=(S.slot.values[pr]==s).astype(float)
    yp=np.asarray(R_[pr,BASEPOL]); knp=np.asarray(X_[pr,BASEPOL])
    t0=time.time(); pp=lab.online_predict(pr,yp,Xp,knp); print("t pooled",time.time()-t0)
    pS3=pp[np.searchsorted(pr,ROWS)]
    v=IN25&~np.isnan(pS3); print("IC pooled", np.corrcoef(pS3[v],y3[v])[0,1])
    evalskip(pS3<0, f"{BASEPOL} ML pooled reg pred<0")
    np.save(f"ml_{BASEPOL}.npy",np.stack([p,pc,pS3]))
pd.DataFrame(res).to_pickle("c2.pkl")
