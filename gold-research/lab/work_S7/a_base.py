import sys; sys.path.insert(0,".."); import lab, numpy as np, pandas as pd
rows=np.where(lab.SIG.slot.values=="S7")[0]
R_=lab.load_R(); X_=lab.load_X(); MF=lab.load_MF()
np.save("R7.npy", np.asarray(R_[rows]).astype(np.float32)); np.save("X7.npy", np.asarray(X_[rows])); np.save("rows7.npy", rows)
np.save("MF7.npy", np.asarray(MF[rows]).astype(np.float32))
m,rr,R=lab.evaluate("S7"); print(m)
t=lab.TIME[rr]; X=np.array([X_[i,lab.baseline_policy("S7")] for i in rr])
df=pd.DataFrame(dict(t=t.tz_localize(None),R=R,hold_h=(X-lab.SIG.m1.values[rr])/60,dir=lab.SIG.dir.values[rr]))
mon=df.groupby(df.t.dt.to_period("M")).agg(n=("R","size"),sumR=("R","sum"),win=("R",lambda x:(x>0).mean()),maxR=("R","max"),hold_h=("hold_h","median"))
print(mon.round(2).to_string())
print("hold hours quantiles", df.hold_h.quantile([.1,.5,.9,1]).round(1).tolist())
print("R quantiles", np.quantile(R,[0,.1,.25,.5,.75,.9,.99,1]).round(2))
print("top10 trades", df.sort_values("R").tail(10).to_string())
print("by dir", df.groupby("dir").R.agg(["size","sum","mean"]))
# all signals (no greedy) per-signal mean
b=lab.baseline_policy("S7"); s=lab.TIME[rows]>=lab.D0
print("all-signal mean R", np.asarray(R_[rows[s],b]).mean(), "n", s.sum())
