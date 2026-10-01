from common import *
exec(open("b_online.py").read().split("G=pd.read_pickle")[0].split("import time")[1])
grid=lab.policy_index(kind="trend",trail="h4q80",rat="none")
grid=[j for j in grid if lab.P[j]["part"] in ("slot","none")]
print(len(grid))
grid2=lab.policy_index(kind="trend",trail="h4q50")+lab.policy_index(kind="trend",trail="h4q80")  # 1440 too many
for kind in ["sum","retdd"]:
    for win in [None,6,12]:
        ch,p=online_greedy_select(grid,kind,win)
        m=met(ch); print("grid120",kind,win,{k:m[k] for k in KEYS}); print("   picks",[x[1] for x in p])
