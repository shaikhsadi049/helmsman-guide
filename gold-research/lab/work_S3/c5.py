from common import *
import itertools
F=getF(); u=pd.read_pickle("uni_2168.pkl"); top=list(u.sort_values("abs",ascending=False).f.head(25))
qq=np.asarray(T.tz_localize(None).to_period("Q").astype(str)); v=IN25; y=RR[v,2168]; q=qq[v]
out=[]
for a,b in itertools.combinations(top,2):
    ta=pd.qcut(F[a].values[v],3,labels=False,duplicates="drop"); tb=pd.qcut(F[b].values[v],3,labels=False,duplicates="drop")
    for i in range(3):
        for j in range(3):
            s=(ta==i)&(tb==j)
            if s.sum()<80: continue
            mu=y[s].mean(); qs=[y[s&(q==Q)].mean() for Q in sorted(set(q)) if (s&(q==Q)).sum()>=8]
            out.append(dict(a=a,ta=i,b=b,tb=j,n=s.sum(),mu=mu,qneg=sum(np.array(qs)<0),nq=len(qs)))
df=pd.DataFrame(out).sort_values("mu"); print(df.head(15).round(3).to_string())
print(df.sort_values("mu",ascending=False).head(8).round(3).to_string())
