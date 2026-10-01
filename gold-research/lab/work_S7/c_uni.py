from common import *
F=F7(); EX=82
y=R7[:,EX].astype(float); yc=np.clip(y,-1.5,3)
q=np.asarray(pd.PeriodIndex(T.tz_localize(None),freq="Q").astype(str))
idx=np.where(IN)[0]; res=[]
for f in F.columns:
    x=F[f].values[idx]
    if np.nanstd(x)==0: continue
    try: b=pd.qcut(pd.Series(x).rank(method="first"),5,labels=False).values
    except Exception: continue
    m=pd.Series(yc[idx]).groupby(b).mean().values
    mr=pd.Series(y[idx]).groupby(b).mean().values
    # quarter consistency of Q5-Q1 (clipped)
    d=pd.DataFrame(dict(q=q[idx],b=b,y=yc[idx]))
    qs=d.groupby(["q","b"]).y.mean().unstack()
    diff=(qs[4]-qs[0]); s=np.sign(m[4]-m[0])
    # spearman
    rho=pd.Series(x).corr(pd.Series(yc[idx]),method="spearman")
    res.append(dict(f=f,rho=rho,q1=m[0],q2=m[1],q3=m[2],q4=m[3],q5=m[4],q1raw=mr[0],q5raw=mr[4],cons=int((np.sign(diff)==s).sum()),worstQ=m.argmin()+1))
r=pd.DataFrame(res); r["absrho"]=r.rho.abs()
r=r.sort_values("absrho",ascending=False); r.to_pickle("uni.pkl")
pd.set_option("display.width",250)
print("overall mean clipped",yc[idx].mean().round(3),"raw",y[idx].mean().round(3))
print(r.head(35).round(3).to_string())
