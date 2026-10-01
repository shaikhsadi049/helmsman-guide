from common import *
F=getF()
def pair_rule(a,sa,b,sb,pol,qc=1/3):
    xa=F[a].values; xb=F[b].values; y=RR[:,pol]; kn=XX[:,pol]; skip=np.zeros(len(ROWS),bool)
    for s,e in zip(MS[:-1],MS[1:]):
        te=(M1>=s)&(M1<e); tr=kn<s
        ea=np.nanquantile(xa[tr],qc if sa=="lo" else 1-qc); eb=np.nanquantile(xb[tr],qc if sb=="lo" else 1-qc)
        ca=lambda x:(x<ea) if sa=="lo" else (x>ea); cb=lambda x:(x<eb) if sb=="lo" else (x>eb)
        sel=tr&ca(xa)&cb(xb)
        if sel.sum()>=30 and y[sel].mean()<0: skip[te]=ca(xa[te])&cb(xb[te])
    return skip
for pol in [2168,1208]:
  for a,sa,b,sb in [("day_rng_atr","lo","d1_vol_ratio","hi"),("m5_atr_pct","lo","d1_vol_ratio","hi"),("h4_atr_rank","lo","d1_vol_ratio","hi"),("day_rng_atr","lo","d1_adx","hi")]:
    sk=pair_rule(a,sa,b,sb,pol); i,r=run(pol,~sk); m=short(met(i,r)); print(pol,a,sa,b,sb,"skip%.1f"%(sk[IN25].mean()*100),{k:m[k] for k in ["n","PF","sumR","maxDD_R","months_pos","eq_R2","ulcer_R"]})
