import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab"); import lab, numpy as np, pandas as pd
S=lab.SIG; F=lab.load_F(); R_=lab.load_R()
J=3692
out=[]
for slotset in [['F9'],['F9','F11','F10','F8']]:
    rows=np.where(S.slot.isin(slotset)&(lab.TIME>=lab.D0))[0]
    y=np.asarray(R_[rows,J]); q=lab.TIME[rows].tz_localize(None).to_period('Q').astype(str).values
    for c in F.columns:
        x=F[c].values[rows]
        if np.nanstd(x)==0: continue
        # within-slot rank to pool
        xr=pd.Series(x).groupby(S.slot.values[rows]).rank(pct=True).values
        hi=xr>0.6; lo=xr<0.4
        qq=pd.DataFrame({'q':q,'y':y,'hi':hi,'lo':lo})
        dq=qq.groupby('q').apply(lambda g: g.y[g.hi].mean()-g.y[g.lo].mean())
        ic=pd.Series(x).corr(pd.Series(y),method='spearman')
        qu=pd.qcut(xr,5,labels=False,duplicates='drop'); qm=pd.Series(y).groupby(qu).mean().values
        out.append(dict(set='+'.join(slotset),f=c,ic=ic,d=y[hi].mean()-y[lo].mean(),qsame=max((dq>0).sum(),(dq<0).sum()),nq=dq.notna().sum(),Q=np.round(qm,2)))
D=pd.DataFrame(out); D['a']=D.ic.abs()
pd.set_option('display.width',250); pd.set_option('display.max_colwidth',60)
for s,g in D.groupby('set'): print(s); print(g.sort_values('a',ascending=False).head(25).round(3).to_string())
D.to_csv('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/uni.csv')
