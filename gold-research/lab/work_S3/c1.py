from common import *
F=getF(); pd.set_option('display.width',250)
qq=np.asarray(T.tz_localize(None).to_period("Q").astype(str))
for pol in [2168,1208]:
    y=RR[:,pol]; v=IN25; out=[]
    for c in F.columns:
        x=F[c].values[v]; yy=y[v]; q=qq[v]
        if np.nanstd(x)==0: continue
        try: b=pd.qcut(pd.Series(x).rank(method="first"),5,labels=False).values
        except Exception: continue
        mq=pd.Series(yy).groupby(b).mean()
        lo=b==0; hi=b==4
        # quarter consistency of (top quintile mean - bottom quintile mean) sign
        d=[]
        for Q in sorted(set(q)):
            s=q==Q
            if (s&lo).sum()>5 and (s&hi).sum()>5: d.append(yy[s&hi].mean()-yy[s&lo].mean())
        d=np.array(d); sg=np.sign(mq[4]-mq[0])
        # worst quintile mean and its consistency
        wq=int(np.argmin(mq.values)); wc=sum(1 for Q in sorted(set(q)) if ((q==Q)&(b==wq)).sum()>5 and yy[(q==Q)&(b==wq)].mean()<yy[q==Q].mean())
        out.append(dict(f=c,q1=mq[0],q2=mq[1],q3=mq[2],q4=mq[3],q5=mq[4],spread=mq[4]-mq[0],cons=(np.sign(d)==sg).sum(),nq=len(d),worstq=wq,worst_cons=wc,
                        rho=pd.Series(x).corr(pd.Series(yy),method="spearman")))
    df=pd.DataFrame(out); df["abs"]=df.spread.abs()
    print("policy",pol, "mean",y[v].mean())
    print(df.sort_values("abs",ascending=False).head(40).round(3).to_string())
    df.to_pickle(f"uni_{pol}.pkl")
