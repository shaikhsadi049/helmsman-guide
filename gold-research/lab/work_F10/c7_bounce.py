from common import *
import warnings; warnings.filterwarnings("ignore")
def past_rank(rows,x):
    """causal percentile of x vs own-slot signals before the month"""
    m=M1[rows]; r=np.full(len(rows),np.nan)
    for a,b in zip(MS[:-1],MS[1:]):
        te=(m>=a)&(m<b); tr=m<a
        if te.any(): r[te]=np.searchsorted(np.sort(x[tr]),x[te])/tr.sum()
    return r
def gate(rows,y,kn,flag_fn,prior=10):
    m=M1[rows]; skip=np.zeros(len(rows),bool); act=0
    fl=flag_fn
    for a,b in zip(MS[:-1],MS[1:]):
        te=(m>=a)&(m<b)
        if not te.any(): continue
        tr=(kn<a)&~np.isnan(fl.astype(float))
        lo=tr&fl; hi=tr&~fl
        if lo.sum()>=5 and y[lo].sum()/(lo.sum()+prior)<0 and y[lo].mean()<y[hi].mean(): skip[te]=fl[te]; act+=1
    return skip,act
for s,exs in [("F10",[109,73,96]),("F11",[73,61])]:
    rows=np.where(S.slot.values==s)[0]; rows=rows[np.argsort(M1[rows])]; tgt=T[rows]>=lab.D0
    # in-sample flags with causal thresholds (warm-up rows get thresholds from expanding past too)
    def flag_expanding(f,q):
        x=F[f].values[rows]; m=M1[rows]; th=np.array([np.quantile(x[:i],q) if i>15 else np.nan for i in range(len(rows))]); return x>th
    fam=["m5_rsi2","m15_ret12","m5_z20","m15_streak","m15_rsi2","m15_ret24"]
    comp=np.nanmean(np.stack([pd.Series(F[f].values[rows]).expanding(16).apply(lambda v: (v[:-1]<v[-1]).mean(),raw=True).values for f in fam]),0)
    for ex in exs:
        y=RF[li_(rows),ex]; kn=XF[li_(rows),ex]
        base=short(met(*sim(rows[tgt],ex)))
        print(s,pname(ex),"nofilter",{k:base[k] for k in["n","PF","sumR","maxDD_R","months_pos","q_pos","eq_R2","top5days_pct"]})
        pair=flag_expanding("m5_rsi2",0.5)&flag_expanding("m15_ret12",0.5)
        for nm,fl in [("pair rsi2&ret12 >med",pair),("bounce comp>0.6",comp>0.6),("bounce comp>0.67",comp>0.67),("bounce comp>0.75",comp>0.75)]:
            sk,act=gate(rows,y,kn,fl)
            m=short(met(*sim(rows[tgt],ex,~sk[tgt])))
            print("   ",nm,"active",act,"skipped",sk[tgt].sum(),{k:m[k] for k in["n","PF","sumR","maxDD_R","months_pos","q_pos","eq_R2","ulcer_R","top5days_pct"]})
