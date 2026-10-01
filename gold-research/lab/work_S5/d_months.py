from common import *
import warnings; warnings.filterwarnings('ignore')
F=feats().copy(); F['dir']=S.dir.values[ROWS]
mon=np.asarray(pd.DatetimeIndex(T).tz_localize(None).to_period('M').astype(str))
tab={}
for p in [8,972]:
    i,r=run(p); tab[p]=pd.Series(r).groupby(mon[i]).sum()
    tab[f'n{p}']=pd.Series(r).groupby(mon[i]).size()
tab['signals']=pd.Series(IN).groupby(mon).sum()
t=pd.DataFrame(tab).fillna(0); t=t[t.signals>0]; print(t.round(2).to_string())
i,r=run(972); bad=set(t.index[t[972]<=0.5])
print('bad/flat months under 972:',sorted(bad))
c=['h4_adx','h4_er30','h4_atr_rank','d1_atr_rank','d1_adx','d1_er30','h4_ribbon','d1_ribbon','d1_ret3','h4_di','day_rng_atr','prev_rng_atr','m5_atr_rank','h1_er30','hour','dir','dxy_trend']
g=pd.Series([m in bad for m in mon[i]])
tr=F.iloc[i].reset_index(drop=True)[c]
print(pd.DataFrame({'bad':tr[g.values].mean(),'good':tr[~g.values].mean(),'all_signals_2025':F[IN][c].mean()}).round(2))
# per month signal features
mm=F[IN].groupby(mon[IN])[['h4_adx','h4_er30','d1_atr_rank','h4_ribbon','d1_ret3','dir','day_rng_atr']].mean().round(2)
mm['R972']=t[972]; mm['R8']=t[8]; print(mm.to_string())
# loss streak details
d=pd.DataFrame(dict(t=T[i].tz_localize(None),R=r,dir=S.dir.values[ROWS][i])); print(d[d.R<-0.5].groupby(d.t.dt.to_period('M')).size().to_string())
