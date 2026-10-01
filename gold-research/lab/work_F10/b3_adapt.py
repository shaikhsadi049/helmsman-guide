from common import *
A=lj(be="none",rat="none"); B=lj(be="none",rat="none",sq="k70")
C=[73,96,109,61,86,98,2,72]
regs=[None,"h4_atr_rank","h1_atr_rank","h1_er30","h1_adx","h4_adx","day_rng_atr","h4_er30","m15_atr_rank","hour","h1_z20","d1_atr_rank"]
for s in ["F10","F11"]:
    res=[]
    for pool in ["own","pooled"]:
        sl=[s] if pool=="own" else ["F8","F9","F10","F11"]
        rows=np.where(S.slot.isin(sl).values)[0]; rows=rows[np.argsort(M1[rows],kind="stable")]
        tgt=(S.slot.values[rows]==s)&(T[rows]>=lab.D0)
        for cn,cs in [("all45",A),("k70",B),("small",C)]:
            for rg in regs:
                for nb in ([1] if rg is None else [2,3]):
                    ch=obp(rows,cs,None if rg is None else F[rg].values[rows],nbins=nb)
                    rr,R=sim(rows[tgt],ch[tgt]); m=met(rr,R)
                    res.append(dict(pool=pool,cands=cn,reg=rg,nb=nb,**short(m)))
    d=pd.DataFrame(res); d.to_csv(f"adapt_{s}.csv",index=False)
    print(s); print(d.sort_values("sumR",ascending=False).to_string())
