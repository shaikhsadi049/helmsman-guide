import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd
S=lab.SIG; R_=lab.load_R(); F=lab.load_F()
rows=np.where((S.slot.values=="S6")&(lab.TIME>=lab.D0))[0]
q=lab.TIME[rows].tz_localize(None).to_period("Q").astype(str).values
out=[]
for pol in [2280,1208]:
    y=np.asarray(R_[rows,pol]).astype(float)
    for f in F.columns:
        x=F[f].values[rows]
        if np.nanstd(x)==0: continue
        try: qb=pd.qcut(pd.Series(x).rank(method="first"),5,labels=False).values
        except Exception: continue
        mq=pd.Series(y).groupby(qb).mean()
        d=pd.DataFrame(dict(y=y,b=qb,q=q))
        # per quarter: top-bottom quintile spread (using global quintile edges)
        sp=d.groupby("q").apply(lambda g: g.y[g.b==4].mean()-g.y[g.b==0].mean(), include_groups=False)
        sgn=np.sign(mq[4]-mq[0])
        out.append(dict(pol=pol,f=f,q1=mq[0],q2=mq[1],q3=mq[2],q4=mq[3],q5=mq[4],spread=mq[4]-mq[0],
            cons=int((np.sign(sp.dropna())==sgn).sum()),nq=int(sp.notna().sum()),ic=pd.Series(x).corr(pd.Series(y),method="spearman")))
D=pd.DataFrame(out); D.to_pickle("uni.pkl")
for pol in [2280,1208]:
    d=D[D.pol==pol].copy(); d["a"]=d.ic.abs()
    print("policy",pol); print(d.sort_values("a",ascending=False).head(25).round(3).to_string())
