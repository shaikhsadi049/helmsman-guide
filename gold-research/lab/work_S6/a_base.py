import sys; sys.path.insert(0, ".."); sys.path.insert(0,"."); import lab, numpy as np, pandas as pd, json
S=lab.SIG
print(S.slot.value_counts().sort_index())
rows=np.where(S.slot.values=="S6")[0]
print("S6 rows",len(rows),"2025+",(lab.TIME[rows]>=lab.D0).sum(), S.iloc[rows].tf.unique(), S.iloc[rows].kind.unique())
b=lab.baseline_policy("S6"); print("base pol",b,lab.P[b])
m,rr,R=lab.evaluate("S6"); print(m)
t=lab.TIME[rr]
mon=pd.Series(R,index=t.tz_localize(None).to_period("M")).groupby(level=0).agg(['count','sum','mean'])
print(mon.round(2))
q=pd.Series(R,index=t.tz_localize(None).to_period("Q")).groupby(level=0).agg(['count','sum'])
print(q.round(2))
print(S.iloc[rows].head())
# overlap with S3
r3=np.where(S.slot.values=="S3")[0]
m6=set(S.m1.values[rows]); m3=set(S.m1.values[r3])
print("S3 n",len(r3),"S6 m1 also in S3:",len(m6&m3)/len(m6))
s3m=np.sort(S.m1.values[r3]); 
d=np.abs(S.m1.values[rows][:,None]-s3m[None,:]).min(1)
print("S6 signals with S3 within 60 min:",(d<=60).mean())
