import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd, time
S=lab.SIG; R_=lab.load_R(); X_=lab.load_X()
rows=np.where((S.slot.values=="S6")&(lab.TIME>=lab.D0))[0]
A=np.asarray(R_[rows,:3600]); XX=np.asarray(X_[rows,:3600])
res=[]
for j in range(3600):
    tk=lab.greedy(rows,XX[:,j]); m=lab.metrics(A[tk,j],lab.TIME[rows[tk]]); m["j"]=j; res.append(m)
G=pd.DataFrame(res).set_index("j").join(pd.DataFrame(lab.P[:3600])[["sq","tp","part","be","trail","rat","ts"]])
G["mpos"]=G.months_pos.str.split("/").str[0].astype(int)
G.to_pickle("greedy_all.pkl")
