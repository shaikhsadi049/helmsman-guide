from common import *
import json, warnings; warnings.filterwarnings('ignore')
C3=[8,972]; c3=bestpol_local(C3,known_of(C3))
mon=np.asarray(pd.DatetimeIndex(T).tz_localize(None).to_period('Q').astype(str))
out={}; M={}
for nm,p in [('baseline_8',8),('ratchet_12',12),('IS_972',972),('causal_8vs972',c3)]:
    i,r=run(p); out[nm]=pd.Series(r).groupby(mon[i]).sum(); M[nm]=lab.metrics(r,T[i])
print(pd.DataFrame(out).round(1).to_string())
for k,v in M.items(): print(k,v)
print('causal choice share 972 in 2025+:',(c3[IN]==972).mean().round(2))
cm=pd.Series(c3[IN]).groupby(np.asarray(pd.DatetimeIndex(T[IN]).tz_localize(None).to_period('M').astype(str))).first(); print(cm.to_dict())
def clean(m): return {k:(float(v) if isinstance(v,(np.floating,float,np.integer)) and v is not None else v) for k,v in m.items()}
json.dump({k:clean(v) for k,v in M.items()},open(W+'/final_metrics.json','w'),indent=1)
