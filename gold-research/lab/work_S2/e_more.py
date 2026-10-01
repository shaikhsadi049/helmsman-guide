from common import *
exec(open("b_online.py").read().split("G=pd.read_pickle")[0].split("import time")[1])
print({j:lab.P[j] for j in [1083,1081,81,1281]})
k50=lab.policy_index(kind="trend",sq="k50",trail="h4q80"); print(len(k50))
for kind in ["sum","retdd"]:
    for win in [None,12]:
        ch,p=online_greedy_select(k50,kind,win); m=met(ch); print("k50grid",kind,win,{k:m[k] for k in KEYS}); print("   picks",[x[1] for x in p])
        np.save(f"ch_k50_{kind}_{win}.npy",ch)
known=Xs[:,k50].max(1); ch=lab.online_best_policy(rows,k50,known); m=met(ch); print("obp-mean k50grid",{k:m[k] for k in KEYS}); print(pd.Series(ch[m25]).value_counts().head().to_dict())
# blends: half position on each of two exits
def blend(a,b,take=None):
    R=0.5*(Rs[:,a]+Rs[:,b]); X=np.maximum(Xs[:,a],Xs[:,b]); k=greedy(R,X,take); return lab.metrics(R[k],t[k])
for a,b in [(132,1041),(0,1041),(0,132),(132,1081),(124,1040)]:
    m=blend(a,b); print("blend",a,b,{k:m[k] for k in KEYS})
