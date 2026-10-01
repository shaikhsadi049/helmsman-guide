from common import *
F=pd.read_pickle("F_S2.pkl"); ms=lab._ms()
def keep(pol,take): m=met(pol,take); return {k:m[k] for k in ["n","PF","sumR","maxDD_R","ret_dd","months_pos","eq_R2","top5days_pct","ulcer_R"]}
def online_thr(pol, feats, qs=(0.6,0.7,0.8,0.9), min_n=80, sides=(1,-1), min_gain=0.0):
    """monthly: among feats x side x quantile cutoff, pick the skip-rule maximising past sum(R) of kept signals (gain over no-skip);
    apply only if gain>min_gain. Past = signals with known exit < month start."""
    y=Rs[:,pol]; known=Xs[:,pol]; take=np.ones(len(rows),bool); log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        test=(M1>=a)&(M1<b)
        if not test.any(): continue
        tr=known<a
        if tr.sum()<min_n: continue
        best=(min_gain,None)
        for f in feats:
            x=F[f].values
            for qq in qs:
                for sd in sides:
                    thr=np.nanquantile(x[tr],qq if sd==1 else 1-qq)
                    skip=(x[tr]>thr) if sd==1 else (x[tr]<thr)
                    gain=-y[tr][skip].sum()/tr.sum()   # gain in mean R per signal from skipping
                    if gain>best[0]: best=(gain,(f,sd,thr,qq))
        if best[1]:
            f,sd,thr,qq=best[1]; x=F[f].values
            take[test]=~((x[test]>thr) if sd==1 else (x[test]<thr)); log.append((f,sd,qq,round(best[0],3)))
        else: log.append(None)
    return take,log
for pol in [0,1041,132]:
    print("== pol",pol,"nofilter",keep(pol,None))
    for nm,feats,sides in [("h1_adx_hi",["h1_adx"],(1,)),("d1_ret3_hi",["d1_ret3"],(1,)),("h4_rng20_hi",["h4_rng20_atr"],(1,)),
                           ("ext3_hi",["h1_adx","d1_ret3","h4_rng20_atr"],(1,)),("all169",list(F.columns),(1,-1))]:
        for mg in [0.0,0.05]:
            take,log=online_thr(pol,feats,sides=sides,min_gain=mg)
            print(f"  {nm} mg{mg} skip%={100*(~take[m25]).mean():.0f}",keep(pol,take))
            if nm=="all169" and mg==0.05: print("     ",log)
