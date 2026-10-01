import sys; L="/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab"; sys.path.insert(0,L); import lab, numpy as np, pandas as pd
S=lab.SIG; rows=np.where(S.slot.values=="S4")[0]
print("S4 rows", len(rows), "2025+", (lab.TIME[rows]>=lab.D0).sum(), S.iloc[rows].time.min())
R_=lab.load_R(); X_=lab.load_X()
np.save("R4.npy", np.asarray(R_[rows,:3600])); np.save("X4.npy", np.asarray(X_[rows,:3600])); np.save("rows.npy", rows)
b=lab.baseline_policy("S4"); print("base pol", b, lab.P[b])
m,rr,R=lab.evaluate("S4"); print(m)
t=lab.TIME[rr].tz_localize(None)
mon=pd.Series(R,index=t.to_period("M")).groupby(level=0).agg(['count','sum']); print(mon.round(2).T.to_string())
print(pd.Series(R,index=t.to_period("Q")).groupby(level=0).agg(['count','sum','mean']).round(2))
eq=np.cumsum(R); print("equity path:", np.round(eq[::5],1))
d=pd.Series(R,index=t.floor("D")).groupby(level=0).sum().nlargest(6); print(d)
print("R dist", np.percentile(R,[0,10,25,50,75,90,100]).round(2), "win",(R>0).mean())
print(S.iloc[rows][["tf","dir","atr","k70","f20"]].describe())
