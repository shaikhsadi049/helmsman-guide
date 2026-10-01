from common import *
import warnings; warnings.filterwarnings("ignore")
F=lab.load_F(); ms=lab._ms(); EX=int(sys.argv[1]) if len(sys.argv)>1 else 144
y=R4[:,EX]; known=X4[:,EX]; Fs=F.iloc[rows].reset_index(drop=True)
base_m=M(EX); print("exit",pstr(EX),short(base_m))
res=[]
def rec(name,take):
    m=M(EX,take); res.append(dict(name=name,skip_pct=round(100*(1-take[IN].mean()),1),**short(m)))
# 1) causal online rule: each month choose (feature, side, quantile) maximising past mean-R uplift with min support
def online_rule(feats, qgrid=(0.6,0.7,0.8,0.9), min_keep=0.5, min_hist=150, need_q=0):
    take=np.ones(len(rows),bool); log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m1>=a)&(m1<b)
        if not te.any(): continue
        tr=known<a
        if tr.sum()<min_hist: log.append(None); continue
        best=(0,None)
        for f in feats:
            x=Fs[f].values; xt=x[tr]; yt=y[tr]; ok=~np.isnan(xt)
            for qq in qgrid:
                for side in (1,-1):
                    th=np.nanquantile(xt, qq if side==1 else 1-qq)
                    keep=(xt<=th) if side==1 else (xt>=th)
                    keep&=ok
                    if keep.mean()<min_keep: continue
                    # gain = sum R removed that was negative => maximize kept sum
                    g=yt[keep].sum()-yt[ok].sum()
                    # require consistency: removed part negative in >=need_q of past halves
                    if g>best[0]: best=(g,(f,side,th))
        if best[1]:
            f,side,th=best[1]; x=Fs[f].values[te]
            take[np.where(te)[0]]=~((x>th) if side==1 else (x<th)); log.append((f,side,round(th,2)))
        else: log.append(None)
    return take,log
rec("none",np.ones(len(rows),bool))
uni=pd.read_pickle("uni.pkl")
allf=list(Fs.columns)
for name,feats in [("rule_all169",allf),("rule_ext6",["prev_rng_atr","d1_ret3","h4_rng20_atr","h1_adx","h4_ret24","h4_rsi14"])]:
    take,log=online_rule(feats); rec(name,take); print(name,log[::2])
# 2) fixed IN-SAMPLE univariate filters for reference (q80 cut using full 2025+ quantile)
for f in ["h4_rng20_atr","h1_adx","h4_rsi14","prev_rng_atr","h4_ret24","h1_ribbon"]:
    x=Fs[f].values; th=np.nanquantile(x[IN],0.8); rec("IS_"+f+"<q80",~(x>th))
    # causal version: threshold = past q80 of this slot's signals (expanding), feature fixed (still IS-chosen feature)
    take=np.ones(len(rows),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m1>=a)&(m1<b); hist=m1<a
        th=np.nanquantile(x[hist],0.8); take[te]=~(x[te]>th)
    rec("CAUSALth_"+f+"<q80",take)
# 3) online ML
def ml(name, feats, pooled=False, cls=False, rounds=200, thr=0.0):
    if pooled:
        allr=np.where(S.kind.values=="trend")[0]; allr=allr[np.argsort(S.m1.values[allr],kind="stable")]
        Rg=lab.load_R(); Xg=lab.load_X()
        yy=np.asarray(Rg[allr,EX]); kn=np.asarray(Xg[allr,EX])
        Xf=F.iloc[allr][feats].copy(); Xf["slot"]=S.slot.str[1:].astype(float).values[allr]
        pr=lab.online_predict(allr,(yy>0).astype(float) if cls else yy,Xf,kn,rounds=rounds,
             params=None if not cls else dict(objective="binary",learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7))
        mp=dict(zip(allr,pr)); pred=np.array([mp[i] for i in rows])
    else:
        pred=lab.online_predict(rows,(y>0).astype(float) if cls else y,Fs[feats],known,rounds=rounds,
             params=None if not cls else dict(objective="binary",learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7))
    v=IN&~np.isnan(pred); ic=pd.Series(pred[v]).rank().corr(pd.Series(y[v]).rank())
    take=~(pred<thr) if not np.isnan(thr) else None
    rec(f"{name} ic={ic:.3f}",take)
    np.save(f"pred_{name}_{EX}.npy",pred); return pred
top=list(uni.sort_values("aic",ascending=False).f[:20])  # IS-selected subset (flag)
ext=["prev_rng_atr","d1_ret3","h4_rng20_atr","h1_adx","h4_ret24","h4_rsi14","h4_bbw_rank","h1_ribbon","h4_di","h4_er30","d1_atr_rank","h4_atr_rank","hour"]
ml("ml_all", allf)
ml("ml_ext13", ext)
ml("ml_all_pooled", allf, pooled=True)
ml("ml_ext13_pooled", ext, pooled=True)
p=ml("ml_cls_all", allf, cls=True, thr=0.4)
print(pd.DataFrame(res).to_string())
pd.DataFrame(res).to_pickle(f"filter_{EX}.pkl")
