from common import *
from scipy.stats import spearmanr
EX={"F10":109,"F11":73}
for s in ["F10","F11"]:
    rows=slot_rows(s); y=RF[li_(rows),EX[s]]; q=T[rows].tz_localize(None).to_period("Q").astype(str).values
    out=[]
    for c in F.columns:
        x=F[c].values[rows]
        if np.nanstd(x)==0: continue
        ic=spearmanr(x,y,nan_policy="omit")[0]
        qs=[spearmanr(x[q==k],y[q==k],nan_policy="omit")[0] for k in np.unique(q)]
        cons=np.nansum(np.sign(qs)==np.sign(ic))
        try: b=pd.qcut(pd.Series(x).rank(method="first"),5,labels=False)
        except: continue
        mq=pd.Series(y).groupby(b.values).mean().values
        out.append(dict(f=c,ic=ic,cons=cons,q1=mq[0],q2=mq[1],q3=mq[2],q4=mq[3],q5=mq[4]))
    d=pd.DataFrame(out); d["a"]=d.ic.abs(); d=d.sort_values("a",ascending=False)
    d.to_csv(f"uni_{s}.csv",index=False)
    print(s,"n",len(rows),"mean y",y.mean().round(3)); print(d.head(25).round(3).to_string())
    print("abs IC distribution:",d.a.describe().round(3).to_dict())
    # null: shuffle
    rng=np.random.default_rng(0); mx=[]
    for _ in range(50):
        yp=rng.permutation(y); mx.append(max(abs(spearmanr(F[c].values[rows],yp,nan_policy='omit')[0]) for c in d.f[:169:4]))
    print("perm max|IC| (subset of 1/4 features) median",np.median(mx).round(3))
