from common import *
exec(open("e_blend_online.py").read().split("k50=lab.policy_index")[0].split("import itertools")[1])
import itertools
exec(open("c_online_rules.py").read().split("for pol in")[0].split('F=pd.read_pickle("F_S2.pkl"); ms=lab._ms()')[1])
F=pd.read_pickle("F_S2.pkl")
k50=lab.policy_index(kind="trend",sq="k50",trail="h4q80")
for tk in [4,12]:
    Rc,Xc,log=online_blend(k50,tk,"retdd",None); k=greedy(Rc,Xc); m=lab.metrics(Rc[k],t[k]); print("topk",tk,{x:m[x] for x in KEYS})
Rc=np.load("blend_retdd_None_R.npy"); Xc=np.load("blend_retdd_None_X.npy")
def gm(take=None):
    k=greedy(Rc,Xc,take); m=lab.metrics(Rc[k],t[k]); return {x:m[x] for x in ["n","PF","sumR","maxDD_R","ret_dd","months_pos","eq_R2","top5days_pct","ulcer_R"]}
print("REC nofilter",gm())
# entry filters (trained on proxy leg 1083 outcomes, causal)
for nm,feats in [("h4_rng20",["h4_rng20_atr"]),("h1_adx",["h1_adx"]),("ext3",["h1_adx","d1_ret3","h4_rng20_atr"]),("all169",list(F.columns))]:
    take,log=online_thr(1083,feats,sides=(1,) if nm!="all169" else (1,-1)); print(" filt",nm,f"skip%={100*(~take[m25]).mean():.0f}",gm(take))
for p in ["pred_1041_all_R.npy","pred_1041_pooled.npy","pred_132_all_R.npy","pred_132_pooled.npy"]:
    pr=np.load(p)
    for cut in [-0.2,0]:
        take=~(pr<cut); print(" ML",p,cut,f"skip%={100*(~take[m25]).mean():.0f}",gm(take))
# monthly / quarterly table for REC
k=greedy(Rc,Xc); mo=np.asarray(t.tz_localize(None).to_period("M"))[k]; print(pd.Series(Rc[k]).groupby(mo).agg(["count","sum"]).round(1).T.to_string())
