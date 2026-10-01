from common import *
print(short(M(BASE)))
A=R4[IN]; q=Q[IN]; uq=np.unique(q)
mean=A.mean(0); med=np.median(A,0)
qm=np.stack([A[q==u].mean(0) for u in uq]); qpos=(qm>0).sum(0)
df=pd.DataFrame(dict(mean=mean,med=med,qpos=qpos,minq=qm.min(0)))
for c in ["sq","tp","part","be","trail","rat","ts"]: df[c]=[P[j][c] for j in range(3600)]
print("baseline sig-level", df.loc[BASE].to_dict())
print(df.sort_values("mean",ascending=False).head(25).to_string())
for c in ["sq","tp","part","be","trail","rat","ts"]:
    print(df.groupby(c)[["mean","med","qpos","minq"]].mean().round(3))
# greedy for top 60 by mean + top by minq
cand=list(df.sort_values("mean",ascending=False).index[:40])+list(df.sort_values("minq",ascending=False).index[:20])
cand=list(dict.fromkeys(cand+[BASE]))
res=[]
for j in cand:
    m=M(j); res.append(dict(j=j,pol=pstr(j),**short(m),ret_dd=m["ret_dd"]))
r=pd.DataFrame(res).sort_values("sumR",ascending=False); print(r.to_string())
df.to_pickle("rank.pkl"); r.to_pickle("greedy_top.pkl")
