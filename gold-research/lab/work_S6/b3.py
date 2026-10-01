import pandas as pd, numpy as np
G=pd.read_pickle("greedy_all.pkl"); G=G.drop_duplicates(subset=["n","sumR","maxDD_R","PF"])
print(len(G))
cols=["n","win","PF","sumR","maxDD_R","ret_dd","top5days_pct","months_pos","q_pos","weeks_pos_pct","eq_R2","ulcer_R","sq","tp","part","be","trail","rat","ts"]
# smoothness score: rank-sum of sumR, mpos, eq_R2, -top5, -ulcer
G["score"]=G.sumR.rank()+G.mpos.rank()+G.eq_R2.rank()+(-G.top5days_pct).rank()+(-G.ulcer_R).rank()+G.ret_dd.rank()
print(G.sort_values("score",ascending=False)[cols].head(30).to_string())
print("\nmpos>=16 by sumR"); print(G[G.mpos>=16].sort_values("sumR",ascending=False)[cols].head(25).to_string())
for c in ["sq","tp","part","be","trail","rat","ts"]:
    print(G.groupby(c)[["sumR","mpos","eq_R2","top5days_pct","maxDD_R"]].median().round(2))
