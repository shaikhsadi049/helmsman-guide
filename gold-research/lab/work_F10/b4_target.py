from common import *
sets={"tp@k70h1":lj(be="none",rat="none",sq="k70",hm=1.0),"tp@k70h0.5":lj(be="none",rat="none",sq="k70",hm=0.5),"tp@k70h2":lj(be="none",rat="none",sq="k70",hm=2.0),
 "hm@k70f50":lj(be="none",rat="none",sq="k70",tp="f50"),"sq@f50h1":lj(be="none",rat="none",tp="f50",hm=1.0)}
for s in ["F10","F11"]:
  for pool in ["own","pooled"]:
    sl=[s] if pool=="own" else ["F8","F9","F10","F11"]
    rows=np.where(S.slot.isin(sl).values)[0]; rows=rows[np.argsort(M1[rows],kind="stable")]
    tgt=(S.slot.values[rows]==s)&(T[rows]>=lab.D0)
    for k,cs in sets.items():
        for pr in [20]:
            ch=obp(rows,cs,prior=pr); rr,R=sim(rows[tgt],ch[tgt])
            picks=pd.Series([pname(c) for c in ch[tgt]]).value_counts().to_dict()
            print(s,pool,k,short(met(rr,R)),picks)
