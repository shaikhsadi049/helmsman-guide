from common import *
import json
def tidy(m): return {k:(float(v) if isinstance(v,(np.floating,np.integer)) else v) for k,v in m.items()}
out={}
for s in ["F10","F11"]:
    rows=np.where(S.slot.values==s)[0]
    cands=[3600+j for j in lj(be="none",rat="none",sq="k70",hm=1.0)]
    kn=lab.known_bar(rows,cands)
    ch=lab.online_best_policy(rows,cands,kn)       # official lab learner
    full=np.full(len(S),lab.baseline_policy(s)); full[rows]=ch
    mb,rb,Rb=lab.evaluate(s); mr,rr,Rr=lab.evaluate(s,full)
    picks=pd.Series([pname(c-3600) for c in ch[lab.TIME[rows]>=lab.D0]]).value_counts().to_dict()
    ib=96 if s=="F10" else 61
    mi,ri,Ri=lab.evaluate(s,3600+ib)
    q=lambda rr,R: {str(k):round(float(v),2) for k,v in pd.Series(R,index=lab.TIME[rr].tz_localize(None).to_period("Q")).groupby(level=0).sum().items()}
    mo=lambda rr,R: {str(k):round(float(v),2) for k,v in pd.Series(R,index=lab.TIME[rr].tz_localize(None).to_period("M")).groupby(level=0).sum().items()}
    out[s]=dict(base=tidy(mb),causal_target=tidy(mr),picks=picks,insample=tidy(mi),insample_pol=pname(ib),
        q_base=q(rb,Rb),q_rec=q(rr,Rr),m_base=mo(rb,Rb),m_rec=mo(rr,Rr),q_is=q(ri,Ri))
    print(s,json.dumps(out[s],indent=0))
json.dump(out,open("final_numbers.json","w"),indent=1)
