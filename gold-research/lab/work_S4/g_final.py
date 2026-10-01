from common import *
import json
F=lab.load_F(); h4=F.h4_stack.values[rows]; ms=lab._ms()
def causal_h4(EX):
    y=R4[:,EX]; kn=X4[:,EX]; take=np.ones(len(rows),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m1>=a)&(m1<b); past=(kn<a)&(h4!=1)
        if past.sum()>=5 and y[past].mean()<0: take[te&(h4!=1)]=False
    return take
r=pd.read_pickle("greedy_all.pkl"); r["rdd"]=r.sumR/r.maxDD_R
isb=r.sort_values("rdd",ascending=False).iloc[0]; print("IS best ret/DD:", isb.j, pstr(int(isb.j)), isb.sumR, isb.maxDD_R)
isb2=r.sort_values("sumR",ascending=False).iloc[0]; print("IS best sumR:", isb2.j, pstr(int(isb2.j)))
out={}
Mo=lambda i: T[i].tz_localize(None).to_period("M")
mt={}
for nm,EX,filt in [("baseline",BASE,False),("k50_atr4_be",144,False),("k50_atr4_be+h4",144,True),("k70_atr4",1304,False),("k70_atr4+h4",1304,True),
                   ("IS_best_retdd",int(isb.j),False),("IS_best_sumR",int(isb2.j),False)]:
    take=causal_h4(EX) if filt else None
    i,rr=greedy_local(EX,take); m=lab.metrics(rr,T[i]); out[nm]=m; mt[nm]=pd.Series(rr,index=Mo(i)).groupby(level=0).sum().round(1)
    print(f"{nm:16s}",short(m),"ret_dd",m["ret_dd"])
# causal counterpart
ch=np.load("ch_sumR2.npy")
for nm,take in [("causal_shadow",None),("causal_shadow+h4",h4==1)]:
    i,rr=greedy_local(ch,take); m=lab.metrics(rr,T[i]); out[nm]=m; mt[nm]=pd.Series(rr,index=Mo(i)).groupby(level=0).sum().round(1); print(f"{nm:16s}",short(m))
pd.set_option("display.width",250); print(pd.DataFrame(mt).T.to_string())
def conv(d): return {k:(float(v) if isinstance(v,(np.floating,np.integer)) else v) for k,v in d.items()}
json.dump({k:conv(v) for k,v in out.items()},open("final_metrics.json","w"),indent=1)
print(pd.DataFrame(mt).T.to_markdown())
