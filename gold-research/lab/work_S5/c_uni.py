from common import *
import warnings; warnings.filterwarnings('ignore')
F=feats().copy(); F['dir']=S.dir.values[ROWS]; F['k50']=S.k50.values[ROWS]; F['f50']=S.f50.values[ROWS]; F['atr']=S.atr.values[ROWS]
q=np.asarray(qtr(T).astype(str))
out=[]
for pol in [8,972]:
    y=RS[:,pol]
    for c in F.columns:
        x=F[c].values.astype(float); v=IN&~np.isnan(x)
        if v.sum()<300: continue
        try: b=pd.qcut(x[v],5,labels=False,duplicates='drop')
        except: continue
        if len(np.unique(b))<3: continue
        g=pd.Series(y[v]).groupby(b).mean()
        lo,hi=g.iloc[0],g.iloc[-1]
        # quarter consistency: sign of (top quintile - bottom quintile) per quarter
        df=pd.DataFrame(dict(y=y[v],b=b,q=q[v])); qs=df.groupby('q').apply(lambda d: d[d.b==b.max()].y.mean()-d[d.b==0].y.mean())
        sp=hi-lo; cons=(np.sign(qs)==np.sign(sp)).sum()
        ic=pd.Series(x[v]).corr(pd.Series(y[v]),method='spearman')
        out.append(dict(pol=pol,f=c,q1=lo,q5=hi,spread=sp,ic=ic,qcons=cons,nq=qs.notna().sum(),means=' '.join(f'{z:.2f}' for z in g.values)))
D=pd.DataFrame(out); D.to_pickle(W+'/uni.pkl')
pd.set_option('display.width',250); pd.set_option('display.max_rows',100)
for pol in [8,972]:
    d=D[D.pol==pol].copy(); d['a']=d.ic.abs()
    print(pol); print(d.sort_values('a',ascending=False).head(30).round(3).to_string())
