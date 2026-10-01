from common import *
import pickle, sys
F=F7(); ms=np.load("ms.npy")
out={}
for EX in (82,130):
    y=R7[:,EX].astype(float); yc=np.clip(y,-1.5,3); known=X7[:,EX]
    W=(~IN)&(known<ms[0])   # warm-up signals RESOLVED before 2025-01-01
    rho=F[W].corrwith(pd.Series(yc[W],index=F.index[W]),method="spearman").dropna()
    rk=rho.abs().sort_values(ascending=False)
    print("EXIT",pname(EX),"warm-up resolved n",W.sum()); print(" top warm-up features:", rho[rk.index[:15]].round(3).to_dict())
    print(" no filter", short(met(EX)))
    for K in (10,15):
        cs=list(rk.index[:K])
        for seed in (7,11,23):
            p=dict(objective="regression",learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=seed)
            pred=lab.online_predict(rows,yc,F[cs],known,params=p); take=~(pred<0)
            out[(EX,K,seed)]=(pred,take,cs)
            print(f" warmsel-top{K} seed{seed} skip={1-take[IN].mean():.2f}",short(met(EX,take)))
    # single fixed feature (top warm-up), threshold = causal past quantile, skip worst side 20%
    f=rk.index[0]; s=-np.sign(rho[f]); x=F[f].values*s; take=np.ones(len(rows),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        te=(M>=a)&(M<b); tr=known<a; take[te]=~(x[te]>np.nanquantile(x[tr],0.8))
    out[(EX,"thr",f)]=take; print(f" thr {f} skip top20%",short(met(EX,take)))
pickle.dump(out,open("warmsel.pkl","wb"))
