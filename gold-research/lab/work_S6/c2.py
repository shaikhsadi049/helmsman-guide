import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd
S=lab.SIG; R_=lab.load_R(); F=lab.load_F(); N=len(S); ms=lab._ms(); M1=S.m1.values
r6=np.where(S.slot.values=="S6")[0]; r3=np.where(S.slot.values=="S3")[0]; pool=np.r_[r6,r3]
K=("n","PF","sumR","maxDD_R","months_pos","q_pos","top5days_pct","eq_R2","ulcer_R")
def show(name,choice,take):
    m,rr,R=lab.evaluate("S6",choice,take); print(f"{name:45s}",{k:m[k] for k in K}); return m
for E in [2280,1208]:
    print("==== exit",E)
    show("no filter",E,None)
    y=np.asarray(R_[:,E]).astype(float)
    for tr_rows,nm in [(r6,"S6"),(pool,"pool")]:
        known=lab.known_bar(tr_rows,[E])
        for f in ["h4_slope50","h4_rng20_atr","h4_ret24","h4_adx","h1_adx","d1_z20","d1_rngpos20","h4_di","vol60_vs_day","h1_ribbon","d1_ret3","h4_ret12","h1_ret48"]:
            x=F[f].values; take=np.ones(N,bool)
            for a,b in zip(ms[:-1],ms[1:]):
                te=r6[(M1[r6]>=a)&(M1[r6]<b)]; tr=tr_rows[known<a]
                if len(te)==0 or len(tr)<100: continue
                ed=np.nanquantile(x[tr],[.2,.4,.6,.8]); bt=np.searchsorted(ed,x[tr]); mu_all=np.nanmean(y[tr])
                mu=np.array([(y[tr][bt==k].sum()+20*mu_all)/((bt==k).sum()+20) for k in range(5)])
                bad=np.where(mu<0)[0]
                take[te]=~np.isin(np.searchsorted(ed,x[te]),bad)
            show(f"  rule {nm} {f}",E,take)
