from common import *
import pickle, sys
F=F7(); EX=int(sys.argv[1]) if len(sys.argv)>1 else 82
ms=np.load("ms.npy")
y=R7[:,EX].astype(float); yc=np.clip(y,-1.5,3); known=X7[:,EX]
print("exit",pname(EX),"nofilter",short(met(EX)))
def online_thresh(f, qs=(0.6,0.7,0.8,0.9), fixed_sign=None, fixed_q=None, prior=50):
    x=F[f].values.astype(float); take=np.ones(len(rows),bool); log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=(M>=a)&(M<b); tr=known<a
        xt,yt=x[tr],yc[tr]
        sgn=fixed_sign if fixed_sign is not None else -np.sign(pd.Series(xt).corr(pd.Series(yt),method="spearman"))
        # sgn=+1: skip HIGH values ; sgn=-1: skip LOW values
        z=xt*sgn; best=(np.inf,0.0)  # (cutoff, gain)
        cands=[fixed_q] if fixed_q else qs
        for qq in cands:
            c=np.nanquantile(z,qq); kept=z<=c
            gain=-(yt[~kept].sum())/(1+prior/ max(1,(~kept).sum()))  # removing negative-sum tail = gain
            if fixed_q or gain>best[1]: best=(c,gain)
        take[te]=~(x[te]*sgn>best[0])
        log.append((round(float(sgn)),best[0]))
    return take,log
out={}
for f in ["h1_adx","h4_rng20_atr","h1_ribbon","h4_di","h4_rsi14","h1_slope50","h4_ret12","h4_dist20","h1_rng20_atr","d1_ret3"]:
    tk,log=online_thresh(f); out[f"thr_learned|{f}"]=tk
    tk2,_=online_thresh(f,fixed_sign=1,fixed_q=0.8); out[f"thr_skipTop20|{f}"]=tk2
    print(f"{f:14s} learned ", short(met(EX,tk)), "skip", round(1-tk[IN].mean(),2))
    print(f"{'':14s} top20%  ", short(met(EX,tk2)), "skip", round(1-tk2[IN].mean(),2))
pickle.dump(out,open(f"filters_thr_{EX}.pkl","wb"))
