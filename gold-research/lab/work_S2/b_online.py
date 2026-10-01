from common import *
import time
ms=lab._ms(); MON=lab.MONTHS
def score(R,X,k,kind):
    if kind=="sum": return R.sum()
    if kind=="retdd":
        eq=np.cumsum(R); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max(); return R.sum()/max(dd,1.0)
    if kind=="mean": return R.mean() if len(R) else -9
def online_greedy_select(cands, kind="sum", window=None, train_mask=None):
    """per month: for each candidate, simulate greedy on past signals whose exit (under that cand) < month start; pick best score"""
    choice=np.full(len(rows),cands[0]); picks=[]
    for a,b,mo in zip(ms[:-1],ms[1:],MON[:-1]):
        test=(M1>=a)&(M1<b)
        if not test.any(): continue
        lo = 0 if window is None else ms[max(0,list(ms).index(a))] - window*30*1440
        best=None; bs=-1e9
        for j in cands:
            ok=(Xs[:,j]<a)&(M1>=lo)
            if train_mask is not None: ok&=train_mask
            free=-1; Rk=[]
            for k in np.where(ok)[0]:
                if M1[k]>free: Rk.append(Rs[k,j]); free=Xs[k,j]
            Rk=np.array(Rk); s=score(Rk,None,None,kind) if len(Rk) else -9
            if s>bs: bs=s; best=j
        choice[test]=best; picks.append((str(mo)[:7],best))
    return choice, picks
G=pd.read_pickle("greedy_all.pkl")
# candidate sets
curated=[0,1032,1040,1041,1072,1073,88,128,132,1329,345,385,213,1064,2273,2241]
families={"curated16":curated}
# broad: one per (sq,tp,part,be,trail in {h4q80,atr4},rat in {none,q70k50},ts) -> ~ 3*5*3*2*2*2*2=720 ; too many for loop -> use mean selector for broad
t0=time.time()
for name,c in families.items():
    for kind in ["sum","retdd"]:
        for win in [None,6,12]:
            ch,p=online_greedy_select(c,kind,win)
            m=met(ch); print(name,kind,win,{k:m[k] for k in KEYS}, round(time.time()-t0))
            print("   picks",[x[1] for x in p])
# lab's online_best_policy (per-signal mean) on curated and all 3600
rows_all=rows
for c,nm in [(curated,"curated"),(list(range(3600)),"all3600")]:
    known=Xs[:,c].max(1)
    ch=lab.online_best_policy(rows_all,c,known); m=met(ch); print("obp-mean",nm,{k:m[k] for k in KEYS}); print("   ",pd.Series(ch[m25]).value_counts().head(5).to_dict())
