from common import *
import warnings; warnings.filterwarnings('ignore')
F=feats().copy(); F['dir']=S.dir.values[ROWS].astype(float)
for c in ['k50','f50','atr']: F[c]=S[c].values[ROWS]
K=['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','eq_R2','ulcer_R','top5days_pct']
ms=lab._MS
def online_rule(x,y,known,nb=5,prior=10,minn=150):
    """each month: past-known signals -> quantile buckets of x; skip bucket if shrunk past mean R < 0"""
    take=np.ones(len(ROWS),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        test=(M1>=a)&(M1<b); tr=(known<a)&~np.isnan(x)
        if not test.any() or tr.sum()<minn: continue
        e=np.nanquantile(x[tr],np.linspace(0,1,nb+1)[1:-1]); bt=np.searchsorted(e,x[tr]); bs=np.searchsorted(e,x[test])
        mu0=y[tr].mean(); bad=[]
        for k in range(nb):
            s=bt==k; mu=(y[tr][s].sum()+prior*mu0)/(s.sum()+prior)
            if mu<0: bad.append(k)
        tk=~np.isin(bs,bad); tk[np.isnan(x[test])]=True; take[np.where(test)[0]]=tk
    return take
out=[]
for pol in [972,8]:
    y=RS[:,pol]; known=XS[:,pol]; b=met(pol)
    for c in F.columns:
        tk=online_rule(F[c].values.astype(float),y,known)
        m=met(pol,tk); out.append(dict(pol=pol,f=c,cov=tk[IN].mean(),**{k:m[k] for k in K}))
D=pd.DataFrame(out); D.to_pickle(W+'/rules.pkl'); pd.set_option('display.width',250)
for pol in [972,8]:
    d=D[D.pol==pol]; print(pol, 'baseline', {k:met(pol)[k] for k in K})
    print(d.sort_values('ret_dd',ascending=False).head(20).to_string())
    print('share of features improving ret_dd:', (d.ret_dd>met(pol)['ret_dd']).mean().round(2), ' sumR:',(d.sumR>met(pol)['sumR']).mean().round(2))
