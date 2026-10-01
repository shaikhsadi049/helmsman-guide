from common import *
exec(open("c_online_rules.py").read().split("for pol in")[0].split('F=pd.read_pickle("F_S2.pkl"); ms=lab._ms()')[1])
F=pd.read_pickle("F_S2.pkl"); ms=lab._ms()
Rc=np.load("blend_retdd_None_R.npy"); Xc=np.load("blend_retdd_None_X.npy")
def gm(take=None):
    k=greedy(Rc,Xc,take); m=lab.metrics(Rc[k],t[k]); return {x:m[x] for x in ["n","PF","sumR","maxDD_R","ret_dd","months_pos","eq_R2","top5days_pct","ulcer_R"]}
d=S.dir.values[rows]
print("in-sample longs only",gm(d>0))
# causal side rule on proxy 1083
for pol in [1083,0]:
    y=Rs[:,pol]; known=Xs[:,pol]; take=np.ones(len(rows),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        test=(M1>=a)&(M1<b); tr=known<a
        for s in [1,-1]:
            past=tr&(d==s)
            if past.sum()>=20 and y[past].mean()<0: take[test&(d==s)]=False
    print("causal side rule",pol,f"skip%={100*(~take[m25]).mean():.0f}",gm(take))
for f in ["d1_er30","d1_adx","h4_atr_rank","d1_dist200"]:
    take,log=online_thr(1083,[f],sides=(-1,)); print("low-",f,f"skip%={100*(~take[m25]).mean():.0f}",gm(take))
