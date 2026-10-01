from common import *
import pickle, lightgbm as lgb
EX=82; F=F7(); ms=np.load("ms.npy")
y=R7[:,EX].astype(float); yc=np.clip(y,-1.5,3); known=X7[:,EX]
W=~IN
print("warm-up n",W.sum())
for f in ["h1_adx","h4_rng20_atr","h1_ribbon","h4_di","h4_rsi14","h1_slope50","h4_ret12","d1_ret3"]:
    print(f, "warmup rho", round(pd.Series(F[f].values[W]).corr(pd.Series(yc[W]),method="spearman"),3))
Xa=F.values.astype(np.float32); cols=np.array(F.columns)
params=dict(objective="regression",learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7)
out={}
for K in (5,10,15):
    pred=np.full(len(rows),np.nan); thr_take=np.ones(len(rows),bool); sel_log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=(M>=a)&(M<b); tr=known<a
        rho=pd.DataFrame(Xa[tr]).corrwith(pd.Series(yc[tr]),method="spearman").abs().fillna(0).values
        top=np.argsort(-rho)[:K]; sel_log.append(list(cols[top[:3]]))
        mdl=lgb.train(params,lgb.Dataset(Xa[tr][:,top],yc[tr]),200)
        pred[te]=mdl.predict(Xa[te][:,top])
    take=~(pred<0); out[K]=(pred,take)
    v=IN&~np.isnan(pred); ic=pd.Series(pred[v]).corr(pd.Series(yc[v]),method="spearman")
    print(f"causal-top{K} ML IC={ic:.3f} skip={1-take[IN].mean():.2f}",short(met(EX,take)))
    print("   top3 by month:",sel_log[0],sel_log[6],sel_log[-1])
# causal single-feature threshold: each month pick feature with largest past |rho|, skip worst 20% side
x_take=np.ones(len(rows),bool); logs=[]
for a,b in zip(ms[:-1],ms[1:]):
    te=(M>=a)&(M<b); tr=known<a
    r=pd.DataFrame(Xa[tr]).corrwith(pd.Series(yc[tr]),method="spearman").fillna(0).values
    k=int(np.argmax(np.abs(r))); s=-np.sign(r[k]); z=Xa[tr][:,k]*s; c=np.quantile(z,0.8)
    x_take[te]=~(Xa[te][:,k]*s>c); logs.append(cols[k])
out["thr_causal_feat"]=x_take
print("causal best-feature skip-top20",short(met(EX,x_take)),"feats:",pd.Series(logs).value_counts().to_dict())
pickle.dump(out,open("causalsel.pkl","wb"))
