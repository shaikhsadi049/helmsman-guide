import sys; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
S=lab.SIG; F=lab.load_F(); R_=lab.load_R()
def pid(sq,tp,hm=1.0): return lab.policy_index(kind='fade',sq=sq,tp=tp,be='none',rat='none',hm=hm)[0]
rows=np.where((S.slot=='F8')&(lab.TIME>=lab.D0))[0]; mo=lab.TIME[rows].tz_localize(None).to_period('M')
tab={}
for n,j in [('base',lab.baseline_policy('F8')),('k50f50',pid('k50','f50')),('k90f50',pid('k90','f50')),('k50f70',pid('k50','f70'))]:
    rr,R,X=lab.run_slot('F8',j); tab[n]=pd.Series(R,index=lab.TIME[rr].tz_localize(None).to_period('M')).groupby(level=0).sum()
    tab[n+'_all']=pd.Series(np.asarray(R_[rows,j]),index=mo).groupby(level=0).mean()
tab['nsig']=pd.Series(1,index=mo).groupby(level=0).sum()
T=pd.DataFrame(tab).round(2); print(T.to_string())
# diagnosis on all signals per month: bad months = ungreedy mean R of k50f50 <0
y=np.asarray(R_[rows,pid('k50','f50')])
bad=T.index[T['k50f50_all']<0]; print('bad months',list(bad))
fs=['h4_er10','h4_adx','h1_adx','h1_er30','d1_er10','d1_adx','d1_ret12','d1_atr_rank','d1_atr_ratio','h4_atr_ratio','day_rng_atr','prev_rng_atr','vol60_vs_day','m15_atr_rank','m15_bar_atr','m15_rsi2','h4_ribbon','dxy_ret5','hour']
Fx=F[fs].iloc[rows].copy(); Fx['dir']=S.dir.values[rows]; Fx['bad']=mo.isin(bad); Fx['mfe']=S.mfe_a.values[rows]; Fx['mae']=S.mae_a.values[rows]
g=Fx.groupby('bad').mean().T; sd=Fx[fs+['dir','mfe','mae']].std()
g['z']=(g[True]-g[False])/sd; print(g.round(3).sort_values('z').to_string())
# direction by month
print(pd.crosstab(mo,S.dir.values[rows],values=y,aggfunc='mean').round(2))
