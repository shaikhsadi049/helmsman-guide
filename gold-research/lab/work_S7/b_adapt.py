from common import *
F=F7()
C=dict(base=BASE, j130=130, j90=90, j82=82, k70_ratq90=pidx(sq="k70",tp="none",part="none",be="none",trail="h4q80",rat="q90k50",ts="none")[0],
       k50_rat2R_be=pidx(sq="k50",tp="none",part="none",be="be1",trail="h4q50",rat="2R_k50",ts="none")[0])
for k,j in C.items(): print(k,j,pname(j),short(met(j)))
# monthly table for key fixed choices
mt=pd.DataFrame({k:monthly(j) for k,j in C.items()}).round(1); print(mt.to_string()); mt.to_pickle("monthly_fixed.pkl")
def ob(cands, regime=None, nbins=3, prior=20):
    known=lab.known_bar(rows,cands)
    ch=lab.online_best_policy(rows,cands,known,regime=regime,nbins=nbins,prior=prior)
    return ch
res={}
# 1) causal best-fixed over ALL 3600 trend policies
allc=list(range(3600)); ch=ob(allc); res["causal_best_of_3600"]=ch
print("causal pick by month:", pd.Series([pname(c) for c in ch[IN]],index=T[IN].tz_localize(None).to_period("M")).groupby(level=0).first().to_string())
# 2) small set: part x rat x sq
small=[pidx(sq=s,tp="none",part=p,be="none",trail="h4q80",rat=r,ts="none")[0] for s in ("k50","k70") for p in ("slot","none") for r in ("none","q90k50","2R_k50")]
res["causal_small12"]=ob(small)
for f in ["h4_er30","h4_atr_rank","d1_atr_rank","h4_adx","h1_er30","day_rng_atr","m15_atr_rank","h4_dist20","d1_er30","hour","h1_adx","d1_adx"]:
    res[f"small12|{f}"]=ob(small,regime=F[f].values.astype(float))
for k,ch in res.items(): print(f"{k:28s}", short(met(ch)))
import pickle; pickle.dump(res,open("adapt.pkl","wb"))
