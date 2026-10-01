from common import *
F=lab.load_F().iloc[rows].reset_index(drop=True); F.to_pickle("F_S2.pkl")
q=np.asarray(t.tz_localize(None).to_period("Q"))
out=[]
for pol in [0,1041,132]:
    y=Rs[:,pol]
    for c in F.columns:
        x=F[c].values; v=m25&~np.isnan(x)
        if v.sum()<500 or np.nanstd(x[v])==0: continue
        try: qb=pd.qcut(x[v],5,labels=False,duplicates="drop")
        except: continue
        if qb.max()<4: continue
        mq=pd.Series(y[v]).groupby(qb).mean()
        # spread top-bottom quintile; per quarter sign consistency of corr
        sp=mq.iloc[-1]-mq.iloc[0]
        dfq=pd.DataFrame({"x":x[v],"y":y[v],"q":q[v]})
        cs=dfq.groupby("q").apply(lambda d: np.corrcoef(d.x,d.y)[0,1] if len(d)>20 and d.x.std()>0 else np.nan)
        ic=pd.Series(x[v]).rank().corr(pd.Series(y[v]).rank())
        cons=(np.sign(cs)==np.sign(ic)).sum()
        out.append(dict(pol=pol,f=c,ic=ic,q1=mq.iloc[0],q5=mq.iloc[-1],spread=sp,qcons=f"{cons}/{cs.notna().sum()}",cons=cons,qmin=mq.min(),qmax=mq.max(),mono=pd.Series(mq.values).corr(pd.Series(range(len(mq))))))
U=pd.DataFrame(out); U.to_pickle("uni.pkl"); pd.set_option("display.width",250)
for pol in [0,1041,132]:
    u=U[U.pol==pol].copy(); u["a"]=u.ic.abs()
    print("== pol",pol); print(u.sort_values("a",ascending=False).head(25).round(3).to_string())
