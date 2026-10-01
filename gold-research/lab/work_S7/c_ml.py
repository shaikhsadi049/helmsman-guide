from common import *
import pickle, sys, time
EX=int(sys.argv[1]) if len(sys.argv)>1 else 82
Fall=lab.load_F(); R_=lab.load_R(); X_=lab.load_X()
F=Fall.iloc[rows].reset_index(drop=True)
y=R7[:,EX].astype(float); yc=np.clip(y,-1.5,3); known=X7[:,EX].astype(np.int64)
print("exit",pname(EX),short(met(EX)))
EXT=["h1_adx","h4_rng20_atr","h1_ribbon","h4_di","h4_rsi14","h1_slope50","h4_ret12","h4_dist20","h1_rng20_atr","d1_ret3","h4_adx","h4_er10","d1_z20","m15_dist200","h1_ret48"]
VOL=["m5_atr_rank","m5_bbw_rank","h4_atr_rank","d1_atr_rank","h1_atr_rank","day_rng_atr","vol60_vs_day","m15_atr_ratio"]
out={}
def ev(nm,pred,thr=0.0):
    take=~(pred<thr); out[nm]=(pred,take)
    v=IN&~np.isnan(pred); ic=pd.Series(pred[v]).corr(pd.Series(yc[v]),method="spearman")
    print(f"{nm:34s} IC={ic:.3f} skip={1-take[IN].mean():.2f}",short(met(EX,take)))
t0=time.time()
ev("ml_all_reg", lab.online_predict(rows,yc,F,known))
ev("ml_ext_reg", lab.online_predict(rows,yc,F[EXT],known))
ev("ml_extvol_reg", lab.online_predict(rows,yc,F[EXT+VOL],known))
pc=dict(objective="binary",learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7)
p=lab.online_predict(rows,(y>0).astype(float),F[EXT+VOL],known,params=pc)
# skip when P(win) below past base-rate*0.8 -> use fixed: below 0.25 (approx break-even given payoff)
for th in (0.25,0.3):
    ev(f"ml_extvol_cls<{th}", p-th)
print("t",time.time()-t0)
# pooled with siblings S1..S6 under the same exit index (trend kind)
sl=lab.SIG.slot.values; pr=np.where(np.isin(sl,["S1","S2","S3","S4","S5","S6","S7"]))[0]
pr=pr[np.argsort(lab.SIG.m1.values[pr],kind="stable")]
yp=np.clip(np.asarray(R_[pr,EX],float),-1.5,3); kp=np.asarray(X_[pr,EX]).astype(np.int64)
for cols,nm in [(EXT+VOL,"pool_extvol"),(list(Fall.columns),"pool_all")]:
    Xp=Fall.iloc[pr][cols].copy(); Xp["is_s7"]=(sl[pr]=="S7").astype(float); Xp["slot_id"]=pd.Series(sl[pr]).str[1].astype(float).values
    pp=lab.online_predict(pr,yp,Xp,kp,min_train=300)
    m=pd.Series(pp,index=pr); pred=m.reindex(rows).values
    ev(nm+"_reg",pred)
print("t",time.time()-t0)
pickle.dump(out,open(f"ml_{EX}.pkl","wb"))
