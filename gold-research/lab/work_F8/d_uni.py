import sys; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd
S=lab.SIG; F=lab.load_F(); R_=lab.load_R()
rows=np.where((S.slot=='F8')&(lab.TIME>=lab.D0))[0]
def pid(sq,tp,hm=1.0): return lab.policy_index(kind='fade',sq=sq,tp=tp,be='none',rat='none',hm=hm)[0]
out=[]
for ename,j in [('base',lab.baseline_policy('F8')),('k50f50',pid('k50','f50')),('k50f70',pid('k50','f70'))]:
    y=np.asarray(R_[rows,j]); q=lab.TIME[rows].tz_localize(None).to_period('Q').values
    for c in F.columns:
        x=F[c].values[rows]
        if np.isnan(x).mean()>0.2 or np.nanstd(x)==0: continue
        try: b=pd.qcut(pd.Series(x).rank(method='first'),5,labels=False).values
        except: continue
        mu=pd.Series(y).groupby(b).mean()
        # spread top-vs-bottom quintile, consistency: per quarter sign of (Q5-Q1) diff
        d=pd.DataFrame(dict(y=y,b=b,q=q))
        qq=d[d.b.isin([0,4])].groupby(['q','b']).y.mean().unstack()
        sgn=np.sign(mu[4]-mu[0]); cons=(np.sign(qq[4]-qq[0])==sgn).mean() if 4 in qq and 0 in qq else np.nan
        rho=pd.Series(x).corr(pd.Series(y),method='spearman')
        # worst quintile alone and its quarter consistency of being negative
        wq=int(mu.idxmin()); wcons=(d[d.b==wq].groupby('q').y.mean()<0).mean()
        out.append(dict(exit=ename,f=c,rho=rho,q1=mu[0],q2=mu[1],q3=mu[2],q4=mu[3],q5=mu[4],spread=mu[4]-mu[0],cons=cons,worstq=wq,worst_mu=mu.min(),worst_negq=wcons))
D=pd.DataFrame(out); D.to_csv('d_uni.csv',index=False)
pd.set_option('display.width',250)
for e in ['base','k50f50']:
    d=D[D.exit==e].copy(); d['a']=d.rho.abs(); print(e); print(d.sort_values('a',ascending=False).head(25).round(3).to_string())
