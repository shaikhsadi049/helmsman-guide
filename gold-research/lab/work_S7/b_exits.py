from common import *
q=pd.PeriodIndex(T.tz_localize(None),freq="Q")
Ri=R7[IN][:, :3600].astype(float); qi=q[IN]
mean=Ri.mean(0); med=np.median(Ri,0)
qm=pd.DataFrame(Ri).groupby(np.asarray(qi.astype(str))).mean()
qpos=(qm>0).sum(0).values
df=pd.DataFrame(dict(j=range(3600),name=[pname(j) for j in range(3600)],mean=mean,med=med,qpos=qpos,qmin=qm.min(0).values))
print("baseline per-signal mean",mean[BASE].round(3),"qpos",qpos[BASE])
# component marginal means (per-signal)
for k in ("sq","tp","part","be","trail","rat","ts"):
    df[k]=[P[j][k] for j in range(3600)]
    print(k, df.groupby(k)["mean"].agg(["mean","max"]).round(3).to_dict())
# greedy metrics for all policies (fast enough?)
import time; t0=time.time()
res=[]
for j in range(3600):
    m=met(j); m["j"]=j; m["score"]=score(m); res.append(m)
print("greedy all", time.time()-t0)
g=pd.DataFrame(res); g["name"]=[pname(j) for j in g.j]
g=g.merge(df[["j","mean","med","qpos","qmin"]],on="j")
g.to_pickle("exits_all.pkl")
for k in ("sq","tp","part","be","trail","rat","ts"):
    g[k]=[P[j][k] for j in g.j]
    print(k, g.groupby(k)[["sumR","maxDD_R","eq_R2","score"]].median().round(2).to_dict("index"))
cols=["j","name","n","PF","sumR","maxDD_R","months_pos","q_pos","weeks_pos_pct","eq_R2","top5days_pct","mean","qpos","score"]
print(g.sort_values("score",ascending=False)[cols].head(30).to_string())
print(g.sort_values("sumR",ascending=False)[cols].head(10).to_string())
print(g[g.j==BASE][cols].to_string())
