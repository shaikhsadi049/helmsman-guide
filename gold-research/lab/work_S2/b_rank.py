import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd, json
S=lab.SIG; rows=np.where(S.slot.values=="S2")[0]
Rs=np.asarray(lab.load_R()[rows,:3600]).astype(float); Xs=np.asarray(lab.load_X()[rows,:3600])
np.save("Rs.npy",Rs); np.save("Xs.npy",Xs); np.save("rows.npy",rows)
t=lab.TIME[rows]; m25=t>=lab.D0
P=pd.DataFrame(lab.P[:3600])
q=t.tz_localize(None).to_period("Q")
R25=Rs[m25]; q25=np.asarray(q[m25])
P["mean"]=np.nanmean(R25,0); P["med"]=np.nanmedian(R25,0); P["nan"]=np.isnan(R25).sum(0)
qm=pd.DataFrame(R25).groupby(q25).mean()
P["q_pos"]=(qm>0).sum(0).values; P["q_min"]=qm.min(0).values
P["hold_h"]=np.median((Xs[m25]-S.m1.values[rows][m25][:,None])/60,0)
P["sh"]=P["mean"]/np.nanstd(R25,0)
pd.set_option("display.width",250); pd.set_option("display.max_columns",30)
print(P.sort_values("mean",ascending=False).head(30))
print(P.sort_values("sh",ascending=False).head(20))
print(P.iloc[0])
for c in ["sq","tp","part","be","trail","rat","ts"]:
    print(P.groupby(c)[["mean","med","sh","q_pos","hold_h"]].mean().round(3))
P.to_pickle("prank.pkl")
