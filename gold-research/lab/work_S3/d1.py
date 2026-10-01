from common import *
F=getF(); pd.set_option('display.width',250)
qq=np.asarray(T.tz_localize(None).to_period("Q").astype(str))
# one-at-a-time component changes from base and from 2168
def find(**kw):
    return [j for j in range(3600) if all(P[j][k]==v for k,v in kw.items())][0]
for basej in [1208,2168]:
    b=P[basej]; print("=== from",basej,b)
    for comp,vals in [("sq",["k50","k70","k90"]),("tp",["none","f50","1R","2R","3R"]),("part",["slot","none","half@f30"]),("be",["none","be1"]),("trail",["h4q80","h4q50","atr2","atr4","none"]),("rat",["none","q90k50","q70k50","2R_k50"]),("ts",["none","ts_half"])]:
        for v in vals:
            if v==b[comp]: continue
            kw={k:b[k] for k in ["sq","tp","part","be","trail","rat","ts"]}; kw[comp]=v; j=find(**kw)
            i,r=run(j); m=short(met(i,r)); print(f"  {comp}={v:8s} j={j:4d}", {k:m[k] for k in ["n","PF","sumR","maxDD_R","months_pos","eq_R2","ulcer_R","top5days_pct"]})
# monthly stats
for j in [1208,2168,2288,3128,2369]:
    i,r=run(j); mo=monthly(i,r); print(j,"monthly mean %.2f std %.2f sharpe %.2f worst %.2f"%(mo.mean(),mo.std(),mo.mean()/mo.std(),mo.min()))
    qs=pd.Series(r,index=T[i].tz_localize(None).to_period("Q")).groupby(level=0).sum(); print("   Q:",qs.round(1).to_dict())
# D: bad vs good months (per-signal mean of 2168 and base by month), feature means
mon=np.asarray(T.tz_localize(None).to_period("M").astype(str))
y=RR[:,2168]; v=IN25
mm=pd.Series(y[v]).groupby(mon[v]).agg(['count','mean'])
mb=pd.Series(RR[v,1208]).groupby(mon[v]).mean()
mm['base_mean']=mb; print(mm.round(3).to_string())
bad=[m for m in mm.index if mm.loc[m,'mean']<0.05]; print("bad months (per-signal mean<0.05 under 2168):",bad)
isbad=np.isin(mon,bad)&v; isgood=(~np.isin(mon,bad))&v
Fz=(F-F[v].mean())/F[v].std()
d=(Fz[isbad].mean()-Fz[isgood].mean()).sort_values()
# monthly-level consistency: fraction of bad months whose month-mean is on the same side
mf=Fz[v].groupby(mon[v]).mean()
cons={c:np.mean(np.sign(mf.loc[bad,c]-mf.loc[[m for m in mf.index if m not in bad],c].mean())==np.sign(d[c])) for c in d.index}
dd=pd.DataFrame({"z_diff":d,"cons_badmonths":pd.Series(cons)})
print(dd.head(15).round(2).to_string()); print(dd.tail(15).round(2).to_string())
