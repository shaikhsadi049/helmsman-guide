import sys; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd
b=lab.baseline_policy('F8'); print('base pol',b,lab.P[b])
m,rr,R=lab.evaluate('F8'); print(m)
t=lab.TIME[rr]; s=pd.Series(R,index=t.tz_localize(None))
mon=s.groupby(s.index.to_period('M')).agg(['count','sum','mean',lambda x:(x>0).mean()])
print(mon.round(2).to_string())
q=s.groupby(s.index.to_period('Q')).agg(['count','sum']); print(q.round(1))
rows=np.where((lab.SIG.slot=='F8')&(lab.TIME>=lab.D0))[0]; print('all 2025 signals',len(rows), 'taken',len(rr))
X=lab.load_X(); print('hold min median', np.median(X[rr,b]-lab.SIG.m1.values[rr]))
# exit reason distribution
print(pd.Series(R).describe())
print('by dir', s.groupby(lab.SIG.dir.values[rr]).agg(['count','sum','mean']))
print('by hour', s.groupby(t.hour).agg(['count','sum','mean']).round(2).to_string())
