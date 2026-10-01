from common import *
exec(open("b_online.py").read().split("G=pd.read_pickle")[0].split("import time")[1])
F=pd.read_pickle("F_S2.pkl")
grid=[j for j in lab.policy_index(kind="trend",trail="h4q80")]  # 720 (all but trail)
print(len(grid))
import time; t0=time.time()
for kind in ["sum","retdd"]:
    for win in [None,12]:
        ch,p=online_greedy_select(grid,kind,win)
        m=met(ch); print("grid720",kind,win,{k:m[k] for k in KEYS},round(time.time()-t0)); print("   picks",[x[1] for x in p])
        np.save(f"ch_grid720_{kind}_{win}.npy",ch)
# regime-based per-signal selection among 3 archetypes
c3=[0,132,1041]; known=Xs[:,c3].max(1)
for reg in [None,"h4_atr_rank","d1_adx","h1_adx","h4_rng20_atr","d1_vol_rank","h4_er10","day_rng_atr","hour"]:
    r=None if reg is None else F[reg].values
    ch=lab.online_best_policy(rows,c3,known,regime=r,nbins=3)
    m=met(ch); print("obp3",reg,{k:m[k] for k in KEYS})
