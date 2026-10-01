from common import *
F=pd.read_pickle("F_S2.pkl")
ext=["h1_adx","h1_slope50","h1_ribbon","h4_rng20_atr","d1_ret3","m15_dist200","h4_ret12","d1_bar_atr","h1_ret48","h4_rsi14"]
print(F.loc[m25,ext].corr(method="spearman").round(2))
print(F.loc[m25,ext].describe().round(2))
pols=[0,1041,1073,132,1040]
def ingreedy(pol,take): m=met(pol,take); return {k:m[k] for k in ["n","PF","sumR","maxDD_R","ret_dd","months_pos","eq_R2","top5days_pct","ulcer_R"]}
# in-sample fixed thresholds on 2025+ quantiles
for f in ext[:6]:
    for qq in [0.6,0.7,0.8,0.9]:
        thr=np.nanquantile(F[f].values[m25],qq); take=~(F[f].values>thr)
        print(f,qq,round(thr,2),{p:(ingreedy(p,take)["sumR"],ingreedy(p,take)["maxDD_R"],ingreedy(p,take)["months_pos"]) for p in [0,1041,132]})
