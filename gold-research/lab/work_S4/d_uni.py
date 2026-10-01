from common import *
F=lab.load_F(); Fs=F.iloc[rows].reset_index(drop=True)
EX=144; y=R4[:,EX]
res=[]
for c in Fs.columns:
    x=Fs[c].values
    v=IN&~np.isnan(x)
    if np.unique(x[v]).size<3: continue
    qs=np.nanquantile(x[v],[.2,.4,.6,.8]); b=np.searchsorted(qs,x)
    mq=[y[v&(b==k)].mean() for k in range(5)]
    # quarter consistency: sign of (top quintile - bottom quintile) and spearman per quarter
    sp=[]
    for u in np.unique(Q[IN]):
        s=v&(Q==u)
        if s.sum()>15: sp.append(pd.Series(x[s]).rank().corr(pd.Series(y[s]).rank()))
    sp=np.array(sp); ic=pd.Series(x[v]).rank().corr(pd.Series(y[v]).rank())
    res.append(dict(f=c,ic=ic,q1=mq[0],q2=mq[1],q3=mq[2],q4=mq[3],q5=mq[4],qsame=(np.sign(sp)==np.sign(ic)).sum(),nq=len(sp),worstq=min(mq),bestq=max(mq)))
r=pd.DataFrame(res); r["aic"]=r.ic.abs()
pd.set_option("display.width",200)
print(r.sort_values("aic",ascending=False).head(30).round(3).to_string())
r.to_pickle("uni.pkl")
print("all mean", y[IN].mean().round(3), "n", IN.sum())
