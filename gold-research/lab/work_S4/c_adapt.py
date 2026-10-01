from common import *
F=lab.load_F()
def pi(**kw): return lab.policy_index(kind="trend",rat=kw.pop("rat","none"),ts=kw.pop("ts","none"),**kw)[0]
C={"base":BASE,"k50_atr4_be":pi(sq="k50",tp="none",part="none",be="be1",trail="atr4"),
 "k70_atr4":pi(sq="k70",tp="none",part="none",be="none",trail="atr4"),
 "k50_atr4_1R":pi(sq="k50",tp="1R",part="none",be="none",trail="atr4"),
 "k50_h4q80_q90":pi(sq="k50",tp="none",part="none",be="none",trail="h4q80",rat="q90k50"),
 "k50_h4q80":pi(sq="k50",tp="none",part="none",be="none",trail="h4q80"),
 "k70_h4q80":pi(sq="k70",tp="none",part="none",be="none",trail="h4q80"),
 "k50_1R_atr2":pi(sq="k50",tp="1R",part="none",be="none",trail="atr2"),
 "k50_2R_atr2":pi(sq="k50",tp="2R",part="none",be="none",trail="atr2"),
 "k50_h4q50_be_ts":pi(sq="k50",tp="none",part="none",be="be1",trail="h4q50",ts="ts_half"),
 "k70_1R_atr4":pi(sq="k70",tp="1R",part="none",be="none",trail="atr4")}
import json; json.dump(C,open("cands.json","w"))
for k,j in C.items(): print(f"{k:18s}",j,short(M(j)))
cands=list(C.values())
known=lab.known_bar(rows,cands)
full=lambda loc: (lambda a:(a.__setitem__(rows,loc),a)[1])(np.full(len(S),BASE))
res=[]
def run(name,regime=None,cset=cands,nb=3,prior=20):
    ch=lab.online_best_policy(rows,cset,lab.known_bar(rows,cset),regime=regime,nbins=nb,prior=prior)
    m=M(ch); res.append(dict(name=name,**short(m))); return ch
ch0=run("online_global")
print(pd.Series([P[c]['sq']+'/'+P[c]['tp']+'/'+P[c]['trail']+'/'+P[c]['be'] for c in ch0[IN]]).value_counts())
for f in ["h4_atr_rank","d1_atr_rank","h1_atr_rank","h4_er30","h4_adx","h1_adx","d1_adx","d1_er10","day_rng_atr","hour","h4_ret12","h4_dist20","d1_ret6","h4_atr_ratio","vol60_vs_day","m15_adx"]:
    for nb in (2,3): run(f"{f}_{nb}",F[f].values[rows],nb=nb)
# smaller candidate sets
sub=[C["k50_atr4_be"],C["k50_1R_atr2"],C["k50_h4q80_q90"]]
run("online_global_sub3",cset=sub)
for f in ["h4_atr_rank","d1_atr_rank","h4_er30","h4_adx","day_rng_atr"]:
    run(f"sub3_{f}",F[f].values[rows],cset=sub,nb=2)
print(pd.DataFrame(res).to_string())
