from common import *
import json; C=json.load(open("cands.json"))
out={}
for k in ["base","k50_atr4_be","k70_atr4","k70_1R_atr4","k50_1R_atr2","k50_h4q50_be_ts","k50_h4q80_q90"]:
    i,r=greedy_local(C[k]); out[k]=pd.Series(r,index=T[i].tz_localize(None).to_period("Q")).groupby(level=0).sum().round(1)
print(pd.DataFrame(out).to_string())
out={}
for k in ["base","k50_atr4_be","k70_1R_atr4","k50_h4q50_be_ts"]:
    i,r=greedy_local(C[k]); out[k]=pd.Series(r,index=T[i].tz_localize(None).to_period("M")).groupby(level=0).sum().round(1)
print(pd.DataFrame(out).T.to_string())
# per-signal (no greedy) quarter means
for k in ["base","k50_atr4_be","k70_1R_atr4"]:
    print(k, pd.Series(R4[IN,C[k]],index=Q[IN]).groupby(level=0).mean().round(3).to_dict())
# holding time
for k in ["base","k50_atr4_be","k70_1R_atr4","k50_h4q50_be_ts"]:
    print(k,"median hold min", np.median(X4[IN,C[k]]-m1[IN]))
