import sys; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
S=lab.SIG; F=lab.load_F(); R_=lab.load_R(); X_=lab.load_X()
def pid(sq,tp,hm=1.0): return lab.policy_index(kind='fade',sq=sq,tp=tp,be='none',rat='none',hm=hm)[0]
K=['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','q_pos','eq_R2','ulcer_R']
compact=['h4_er10','h4_er30','h4_adx','h1_adx','h1_er10','h1_er30','d1_er10','d1_adx','d1_ret12','d1_ret6','prev_rng_atr','day_rng_atr','vol60_vs_day',
 'm15_atr_rank','h1_atr_rank','h4_atr_ratio','d1_atr_ratio','m15_bar_atr','m15_rsi2','m15_z20','m15_rng20_atr','day_pos','day_ret_atr','hour','h4_ribbon','h4_dist20','h1_dist20','d1_rngpos20','dxy_ret5']
allf=[c for c in F.columns if not c.endswith('atr_pct')]  # drop price-level-like time proxies
res=[]
for ename,j in [('base',lab.baseline_policy('F8')),('k50f50',pid('k50','f50'))]:
  for pool in ['F8','fades']:
    rows=np.where(S.slot=='F8')[0] if pool=='F8' else np.where(S.kind=='fade')[0]
    y=np.asarray(R_[rows,j]); known=np.asarray(X_[rows,j])
    for fs_name,fs in [('compact',compact),('all',allf)]:
        Xf=F[fs].iloc[rows].copy()
        if pool=='fades':
            for s in ['F8','F9','F10','F11']: Xf['is_'+s]=(S.slot.values[rows]==s).astype(float)
        Xf['dir']=S.dir.values[rows]
        for tgt in ['reg','cls']:
            yy=y if tgt=='reg' else (y>0).astype(float)
            params=None if tgt=='reg' else dict(objective='binary',learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7)
            p=lab.online_predict(rows,yy,Xf,known,min_train=120,params=params)
            f8=S.slot.values[rows]=='F8'
            r8=rows[f8]; p8=p[f8]; post=lab.TIME[r8]>=lab.D0
            ok=~np.isnan(p8[post]); 
            rho=pd.Series(p8[post][ok]).corr(pd.Series(y[f8][post][ok]),method='spearman')
            # thresholds: reg pred<0 skip; cls: p< past-median skip -> use fixed 0.5 & 0.45
            for thr in ([0.0,-0.1] if tgt=='reg' else [0.45,0.5]):
                take=np.ones(len(S),bool); sk=np.nan_to_num(p8,nan=99)<thr; take[r8[sk]]=False
                rr,R,X=lab.run_slot('F8',j,take); m=lab.metrics(R,lab.TIME[rr])
                res.append(dict(exit=ename,pool=pool,fs=fs_name,tgt=tgt,thr=thr,rho=round(rho,3),skip=round(sk[post].mean()*100),**{k:m[k] for k in K}))
                print(res[-1],flush=True)
pd.DataFrame(res).to_csv('f_ml.csv',index=False)
