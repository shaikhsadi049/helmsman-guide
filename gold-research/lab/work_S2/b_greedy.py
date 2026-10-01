from common import *
import time; t0=time.time()
b=lab.baseline_policy("S2"); print(met(b)); print(lab.evaluate("S2")[0])
res=[]
for j in range(3600):
    m=met(j); m["j"]=j; res.append(m)
G=pd.DataFrame(res); P=pd.read_pickle("prank.pkl"); G=G.join(P[["sq","tp","part","be","trail","rat","ts","mean"]],on="j")
G["mp"]=G.months_pos.str.split("/").str[0].astype(int)
G.to_pickle("greedy_all.pkl"); print(time.time()-t0)
pd.set_option("display.width",250); pd.set_option("display.max_columns",30)
cols=["j","sq","tp","part","be","trail","rat","ts","n","win","PF","sumR","maxDD_R","ret_dd","top5days_pct","months_pos","weeks_pos_pct","eq_R2","ulcer_R"]
for s in ["sumR","ret_dd","eq_R2","mp"]:
    print("== by",s); print(G.sort_values([s,"sumR"],ascending=False)[cols].head(15).to_string())
