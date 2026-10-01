import pandas as pd, numpy as np
G=pd.read_pickle("greedy_all.pkl"); pd.set_option("display.width",250)
G["top5"]=G.top5days_pct.astype(float)
for c in ["sq","tp","part","be","trail","rat","ts"]:
    print(G.groupby(c)[["n","sumR","maxDD_R","ret_dd","mp","eq_R2","ulcer_R","top5","PF"]].median().round(2))
# combos sq x tp x part
print(G.groupby(["sq","tp","part"])[["n","sumR","maxDD_R","ret_dd","mp","eq_R2"]].median().round(2).sort_values("ret_dd",ascending=False).head(20))
# how many policies beat baseline on sumR, maxDD, months, eq_R2 together
b=G.iloc[0]; better=(G.sumR>b.sumR)&(G.maxDD_R<=b.maxDD_R)&(G.mp>=b.mp)&(G.eq_R2>b.eq_R2)
print("dominate baseline:",better.sum(),"of",len(G)); print(G[better].groupby(["sq","tp","part"]).size())
