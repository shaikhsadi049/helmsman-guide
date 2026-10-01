from common import *
import time; t0=time.time(); res=[]
for j in range(3600):
    m=M(j); res.append(dict(j=j,**{c:P[j][c] for c in ["sq","tp","part","be","trail","rat","ts"]},**short(m),ret_dd=m["ret_dd"]))
r=pd.DataFrame(res); r["mpos"]=r.months_pos.str.split("/").str[0].astype(int); r["qp"]=r.q_pos.str.split("/").str[0].astype(int)
r.to_pickle("greedy_all.pkl"); print(time.time()-t0)
