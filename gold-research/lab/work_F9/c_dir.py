import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab"); import lab, numpy as np, pandas as pd
S=lab.SIG; F=lab.load_F(); R_=lab.load_R()
for J in [3673,3692]:
  for sl in ['F9','F11','F10','F8']:
    rows=np.where((S.slot==sl)&(lab.TIME>=lab.D0))[0]; y=np.asarray(R_[rows,J]); d=S.dir.values[rows]
    q=lab.TIME[rows].tz_localize(None).to_period('Q').astype(str)
    t=pd.DataFrame({'y':y,'d':d,'q':q}).pivot_table(index='q',columns='d',values='y',aggfunc=['mean','count']).round(2)
    print(J,sl,'buy',y[d==1].mean().round(3),(d==1).sum(),'sell',y[d==-1].mean().round(3),(d==-1).sum())
    if sl=='F9': print(t.T)
rows=np.where((S.slot=='F9')&(lab.TIME>=lab.D0))[0]; y=np.asarray(R_[rows,3692])
for c in ['d1_stack','d1_slope50','h4_stack','h1_dist20','h1_bbw_rank','m5_atr_pct','h1_z20']:
    x=F[c].values[rows]; print(c, pd.Series(y).groupby(pd.qcut(x,4,duplicates='drop')).agg(['mean','count']).round(2).to_dict())
