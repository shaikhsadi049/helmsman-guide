from common import *
import warnings, time; warnings.filterwarnings('ignore')
F=feats().copy(); F['dir']=S.dir.values[ROWS].astype(float)
for c in ['k50','f50','atr','tw50']: F[c]=S[c].values[ROWS]
K=['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','eq_R2','ulcer_R','top5days_pct']
EXT=['d1_ret3','h4_di','h4_adx','h1_ribbon','h4_rng20_atr','d1_z20','h4_slope50','h4_ret24','d1_rngpos20','h1_adx']
VOL=['m15_bbw_rank','d1_vol_ratio','d1_bar_atr','day_rng_atr','h4_bar_atr','m5_atr_pct','k50','f50']
REG=[c for c in F.columns if c.startswith(('h4_','d1_'))]+['dir','day_rng_atr','prev_rng_atr','dxy_trend','dxy_z20']
res={}
for pol in [972,8]:
    y=RS[:,pol]; known=XS[:,pol]
    print('== pol',pol, {k:met(pol)[k] for k in K})
    for nm,cols in [('all',list(F.columns)),('ext',EXT),('ext+vol',EXT+VOL),('htf',REG)]:
        for tgt in ['reg','cls']:
            yy=y if tgt=='reg' else (y>0).astype(float)
            prm=None
            if tgt=='cls': prm=dict(objective='binary',learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7)
            t0=time.time(); pr=lab.online_predict(ROWS,yy,F[cols],known,params=prm)
            v=IN&~np.isnan(pr); ic=pd.Series(pr[v]).corr(pd.Series(y[v]),method='spearman')
            res[(pol,nm,tgt)]=pr
            for thr in ([0] if tgt=='reg' else [0.4,0.5]):
                take=~(pr<thr)
                m=met(pol,take); print(f'{nm:8s} {tgt} thr{thr} ic={ic:.3f} cov={take[IN].mean():.2f}',{k:m[k] for k in K}, f'{time.time()-t0:.0f}s',flush=True)
import pickle; pickle.dump(res,open(W+'/ml_preds.pkl','wb'))
