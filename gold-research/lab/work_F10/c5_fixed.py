from common import *
def causal_q(rows,x,qq):
    """threshold = quantile of x over own-slot signals before this signal's month start (features known at signal time, no outcome needed)"""
    m=M1[rows]; th=np.full(len(rows),np.nan)
    for a,b in zip(MS[:-1],MS[1:]):
        te=(m>=a)&(m<b); tr=m<a
        if te.any() and tr.sum()>20: th[te]=np.nanquantile(x[tr],qq)
    return th
EX={"F10":[73,109,96],"F11":[73,61,86]}
for s in ["F10","F11"]:
    rows=np.where(S.slot.values==s)[0]; rows=rows[np.argsort(M1[rows])]; tgt=T[rows]>=lab.D0
    for ex in EX[s]:
        rr,R=sim(rows[tgt],ex); print(s,pname(ex),"nofilter",short(met(rr,R)))
        for f,side in [("h4_er30","low"),("m15_ret12","high"),("h1_z20","high")]:
            x=F[f].values[rows]
            for qq in [0.2,0.25,0.33,0.4]:
                th=causal_q(rows,x,qq if side=="low" else 1-qq)
                skip=(x<th) if side=="low" else (x>th)
                rr,R=sim(rows[tgt],ex,~skip[tgt]); m=short(met(rr,R))
                print(f"   skip {f} {side} {qq}: skipped {skip[tgt].sum()}",{k:m[k] for k in ["n","PF","sumR","maxDD_R","months_pos","q_pos","eq_R2","top5days_pct"]})
