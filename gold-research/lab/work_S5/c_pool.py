from common import *
import warnings; warnings.filterwarnings('ignore')
K=['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','eq_R2','ulcer_R','top5days_pct']
FA=lab.load_F(); Rm=lab.load_R(); Xm=lab.load_X()
tr_rows=np.where(S.kind.values=='trend')[0]; tr_rows=tr_rows[np.argsort(S.m1.values[tr_rows],kind='stable')]
Xf=FA.iloc[tr_rows].copy(); Xf['dir']=S.dir.values[tr_rows]
for s in ['S1','S2','S3','S4','S5','S6','S7']: Xf['is_'+s]=(S.slot.values[tr_rows]==s).astype(float)
for c in ['k50','f50']: Xf[c]=S[c].values[tr_rows]
pos=pd.Series(np.arange(len(tr_rows)),index=tr_rows)[ROWS].values
EXT=['d1_ret3','h4_di','h4_adx','h1_ribbon','h4_rng20_atr','d1_z20','h4_slope50','h4_ret24','d1_rngpos20','h1_adx','m15_bbw_rank','d1_vol_ratio','d1_bar_atr','day_rng_atr','h4_bar_atr','m5_atr_pct','k50','f50','dir']
for pol in [972,8]:
    y=np.asarray(Rm[tr_rows,pol],float); known=np.asarray(Xm[tr_rows,pol])
    print('== pol',pol,{k:met(pol)[k] for k in K})
    for nm,cols in [('all',list(Xf.columns)),('ext',EXT+['is_S5'])]:
      for tgt in ['reg','cls']:
        prm=None; yy=y
        if tgt=='cls':
            yy=(y>0).astype(float); prm=dict(objective='binary',learning_rate=0.03,num_leaves=8,min_data_in_leaf=50,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7)
        pr=lab.online_predict(tr_rows,yy,Xf[cols],known,min_train=500,params=prm)[pos]
        v=IN&~np.isnan(pr); ic=pd.Series(pr[v]).corr(pd.Series(RS[v,pol]),method='spearman')
        for thr in ([0] if tgt=='reg' else [0.4,0.45,0.5]):
            tk=~(pr<thr); m=met(pol,tk); print(f'{nm} {tgt} thr{thr} ic={ic:.3f} cov={tk[IN].mean():.2f}',{k:m[k] for k in K},flush=True)
