import sys; L="/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/"; sys.path.insert(0,L)
import lab, numpy as np, pandas as pd
S=lab.SIG
rows=np.where(S.slot.isin(["F8","F9","F10","F11"]))[0]
R_=lab.load_R(); X_=lab.load_X(); MF=lab.load_MF()
np.save(L+"work_F10/rows.npy",rows)
np.save(L+"work_F10/Rf.npy",np.asarray(R_[rows,3600:3780]))
np.save(L+"work_F10/Xf.npy",np.asarray(X_[rows,3600:3780]))
for s in ["F10","F11"]:
    m,rr,R=lab.evaluate(s); print(s,m)
    t=lab.TIME[rr]; print(pd.Series(R,index=t.tz_localize(None).to_period("M")).groupby(level=0).agg(['count','sum']).round(2).T.to_string())
    r=np.where(S.slot.values==s)[0]; print("all signals",len(r),"2025+",(lab.TIME[r]>=lab.D0).sum(), S.iloc[r][['tf','atr','k70','f50']].describe().round(2).to_string())
