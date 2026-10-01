import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd, json, time
S=lab.SIG; R_=lab.load_R(); P=lab.P
rows=np.where((S.slot.values=="S6")&(lab.TIME>=lab.D0))[0]
A=np.asarray(R_[rows,:3600]).astype(float)
q=lab.TIME[rows].tz_localize(None).to_period("Q").astype(str).values
pdf=pd.DataFrame(P[:3600])
pdf["mean"]=np.nanmean(A,0); pdf["med"]=np.nanmedian(A,0); pdf["win"]=np.nanmean(A>0,0)
Q=pd.DataFrame(A).groupby(q).mean()
pdf["qpos"]=(Q>0).sum(0).values; pdf["qmin"]=Q.min(0).values
pdf["nan"]=np.isnan(A).sum(0)
b=lab.baseline_policy("S6")
print("all-signal base:",pdf.loc[b,["mean","med","win","qpos","qmin"]].to_dict())
for c in ["sq","tp","part","be","trail","rat","ts"]:
    print(pdf.groupby(c)[["mean","med","win","qmin"]].mean().round(3))
print(pdf.sort_values("mean",ascending=False).head(30).to_string())
pdf.to_pickle("pol_rank.pkl")
# greedy for top 60 by mean + top by qmin + baseline neighbours
top=set(pdf.sort_values("mean",ascending=False).index[:60])|set(pdf.sort_values("qmin",ascending=False).index[:30])
res=[]
t0=time.time()
for j in sorted(top|{b}):
    rr,R,X=lab.run_slot("S6",j); m=lab.metrics(R,lab.TIME[rr]); m["j"]=j; res.append(m)
G=pd.DataFrame(res).set_index("j").join(pdf[["sq","tp","part","be","trail","rat","ts","mean"]])
G.to_pickle("greedy_top.pkl")
print(time.time()-t0)
print(G.sort_values("sumR",ascending=False).head(40).to_string())
print(G.loc[b])
