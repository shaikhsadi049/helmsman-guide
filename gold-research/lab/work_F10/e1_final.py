from common import *
import json
def gated_skip(rows,y,kn,x,qq=0.25,prior=10,pool_rows=None):
    """causal: threshold = past quantile of x (own slot, all signals before month); skip low tail only if past RESOLVED
    signals in the low tail had shrunk mean R < 0 and below the rest."""
    m=M1[rows]; skip=np.zeros(len(rows),bool); act=[]
    for a,b in zip(MS[:-1],MS[1:]):
        te=(m>=a)&(m<b)
        if not te.any(): continue
        th=np.nanquantile(x[m<a],qq); tr=kn<a
        lo=tr&(x<th); hi=tr&(x>=th)
        sm=y[lo].sum()/(lo.sum()+prior)
        on=(sm<0) and (y[lo].mean()<y[hi].mean())
        act.append(int(on))
        if on: skip[te]=x[te]<th
    return skip,act
out={}
for s,ex in [("F10",109),("F11",73),("F11b",61)]:
    sl=s[:3]
    rows=np.where(S.slot.values==sl)[0]; rows=rows[np.argsort(M1[rows])]; tgt=T[rows]>=lab.D0
    y=RF[li_(rows),ex]; kn=XF[li_(rows),ex]; x=F["h4_er30"].values[rows]
    for qq in [0.2,0.25,0.33]:
        sk,act=gated_skip(rows,y,kn,x,qq)
        rr,R=sim(rows[tgt],ex,~sk[tgt]); m=short(met(rr,R))
        print(s,pname(ex),qq,"active months",sum(act),"/",len(act),"skipped",sk[tgt].sum(),m)
        if qq==0.25: out[s]=(rr,R,sk,act)
    rr0,R0=sim(rows[tgt],73)
    rr,R,sk,act=out[s]
    mon=pd.DataFrame({"base":pd.Series(R0,index=T[rr0].tz_localize(None).to_period("M")).groupby(level=0).sum(),
                      "rec":pd.Series(R,index=T[rr].tz_localize(None).to_period("M")).groupby(level=0).sum()}).fillna(0).round(2)
    print(mon.T.to_string())
