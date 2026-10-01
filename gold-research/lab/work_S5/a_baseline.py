import sys; sys.path.insert(0,'..'); sys.path.insert(0,'.'); import lab, numpy as np, pandas as pd
S=lab.SIG
m,rr,R=lab.evaluate('S5'); print(m)
t=lab.TIME[rr]; X=lab.load_X(); b=lab.baseline_policy('S5')
df=pd.DataFrame(dict(t=t.tz_localize(None),R=R,dir=S.dir.values[rr],hold_h=(X[rr,b]-S.m1.values[rr])/60))
print(df.groupby(df.t.dt.to_period('M')).agg(n=('R','size'),sumR=('R','sum'),win=('R',lambda x:(x>0).mean()),hold=('hold_h','median')).round(2))
print(df.groupby(df.t.dt.to_period('Q')).R.agg(['size','sum']))
print(df.groupby('dir').R.agg(['size','sum','mean']))
print('hold h quantiles',df.hold_h.quantile([.1,.5,.9]).round(1).tolist())
print(df.sort_values('R').head(8)); print(df.sort_values('R').tail(8))
# all signals per month (unfiltered) and baseline mean R
rows=np.where((S.slot.values=='S5')&(lab.TIME>=lab.D0))[0]; Rb=np.asarray(lab.load_R()[rows,b])
d2=pd.DataFrame(dict(t=lab.TIME[rows].tz_localize(None),R=Rb))
print(d2.groupby(d2.t.dt.to_period('M')).R.agg(['size','mean','sum']).round(2))
print('all-signal mean',Rb.mean(), 'median',np.median(Rb))
