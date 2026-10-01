from common import *
import json
def clean(m): return {k:(v.item() if hasattr(v,"item") else v) for k,v in m.items()}
Rc=np.load("blend_retdd_None_R.npy"); Xc=np.load("blend_retdd_None_X.npy")
k=greedy(Rc,Xc); rec=clean(lab.metrics(Rc[k],t[k]))
q=np.asarray(t.tz_localize(None).to_period("Q")).astype(str)
out={"baseline":clean(met(0)),"recommended":rec,"rec_q":pd.Series(Rc[k]).groupby(q[k]).sum().round(1).to_dict()}
kb,Rb=run(0); out["base_q"]=pd.Series(Rb).groupby(q[kb]).sum().round(1).to_dict()
R2=0.5*(Rs[:,132]+Rs[:,1041]); X2=np.maximum(Xs[:,132],Xs[:,1041]); k2=greedy(R2,X2); out["is_blend"]=clean(lab.metrics(R2[k2],t[k2])); out["is_blend_q"]=pd.Series(R2[k2]).groupby(q[k2]).sum().round(1).to_dict()
for j in [132,1041]:
    out[f"is_{j}"]=clean(met(j)); kk,RR=run(j); out[f"is_{j}_q"]=pd.Series(RR).groupby(q[kk]).sum().round(1).to_dict()
out["pols"]={j:lab.P[j] for j in [1083,1084,1085,1082,1081,125,81,1041,132,124,3]}
print(json.dumps(out,indent=1,default=str))
json.dump(out,open("dump.json","w"),default=str,indent=1)
