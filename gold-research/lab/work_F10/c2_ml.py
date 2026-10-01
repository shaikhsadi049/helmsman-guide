from common import *
import warnings; warnings.filterwarnings("ignore")
EX={"F10":109,"F11":73}
cols=list(F.columns)
mom=[c for c in cols if any(c.startswith(p) for p in ["m5_","m15_","h1_"]) and any(k in c for k in ["ret","rsi","z20","dist20","streak","rngpos20","body"])]
reg=[c for c in cols if any(k in c for k in ["atr_rank","er30","er10","adx","stack","ribbon","bbw_rank","vol_rank"])]+["day_rng_atr","hour","day_pos","prev_rng_atr"]
subsets={"all":cols,"mom":mom,"regime":reg,"mom+reg":mom+reg}
clsp=dict(objective="binary",learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7)
res=[]
for s in ["F10","F11"]:
    ex=EX[s]
    for pool in ["own","pooled"]:
        sl=[s] if pool=="own" else ["F8","F9","F10","F11"]
        rows=np.where(S.slot.isin(sl).values)[0]; rows=rows[np.argsort(M1[rows],kind="stable")]
        y=RF[li_(rows),ex]; kn=XF[li_(rows),ex]
        tgt=(S.slot.values[rows]==s)&(T[rows]>=lab.D0)
        for sn,fs in subsets.items():
            X=F[fs].iloc[rows].copy()
            if pool=="pooled":
                for k in ["F8","F9","F10","F11"]: X["is_"+k]=(S.slot.values[rows]==k).astype(float)
            mt=60 if pool=="own" else 120
            for mode in ["reg","cls"]:
                if mode=="reg": p=lab.online_predict(rows,y,X,kn,min_train=mt); skip=p<0
                else: p=lab.online_predict(rows,(y>0).astype(float),X,kn,min_train=mt,params=clsp); skip=p<0.5
                v=tgt&~np.isnan(p)
                ic=np.corrcoef(p[v],y[v])[0,1] if v.sum()>10 else np.nan
                take=~(skip&~np.isnan(p))
                rr,R=sim(rows[tgt],ex,take[tgt]); m=short(met(rr,R))
                res.append(dict(slot=s,pool=pool,feat=sn,mode=mode,ic=round(ic,3),cov=round(v.sum()/tgt.sum(),2),skipped=int((~take[tgt]).sum()),**m))
                print(res[-1],flush=True)
pd.DataFrame(res).to_csv("ml.csv",index=False)
