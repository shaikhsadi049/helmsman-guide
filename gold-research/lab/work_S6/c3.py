import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd, time
S=lab.SIG; R_=lab.load_R(); F=lab.load_F(); N=len(S); ms=lab._ms(); M1=S.m1.values
r6=np.where(S.slot.values=="S6")[0]; r3=np.where(S.slot.values=="S3")[0]
K=("n","PF","sumR","maxDD_R","months_pos","q_pos","top5days_pct","eq_R2","ulcer_R")
def show(name,choice,take):
    m,rr,R=lab.evaluate("S6",choice,take); print(f"{name:52s}",{k:m[k] for k in K},flush=True); return m
E=2280
nonstat=[c for c in F.columns if c.endswith("atr_pct")]
allf=[c for c in F.columns if c not in nonstat]
h4d1=[c for c in allf if c[:2] in ("h4","d1")]
cons=["h4_slope50","h4_rng20_atr","h4_ret24","h4_adx","h1_adx","d1_z20","d1_rngpos20","h4_di","vol60_vs_day","h1_ribbon","d1_ret3","h4_ret12","h1_ret48","d1_vol_ratio","h4_ribbon"]
show("no filter",E,None)
for pool in ["S6","pool"]:
    rows=r6 if pool=="S6" else np.r_[r6,r3]; rows=rows[np.argsort(M1[rows])]
    y=np.asarray(R_[rows,E]).astype(float)
    known=lab.known_bar(rows,[E])
    for fs_name,fs in [("all",allf),("h4d1",h4d1),("cons15",cons)]:
        X=F.iloc[rows][fs].copy()
        if pool=="pool": X["is_s6"]=(S.slot.values[rows]=="S6").astype(float)
        for tgt in ["clipR","win"]:
            yy=np.clip(y,-1.5,3) if tgt=="clipR" else (y>0).astype(float)
            t0=time.time(); p=lab.online_predict(rows,yy,X,known)
            v=~np.isnan(p)&(lab.TIME[rows]>=lab.D0)&(S.slot.values[rows]=="S6")
            ic=pd.Series(p[v]).corr(pd.Series(y[v]),method="spearman")
            pf=np.full(N,np.nan); pf[rows]=p
            thr0= 0 if tgt=="clipR" else 0.5
            print(f"-- {pool} {fs_name} {tgt} IC={ic:.3f} {time.time()-t0:.0f}s")
            for lab_,thr in [("pred<thr",thr0)]:
                take=np.ones(N,bool); take[r6]=~(pf[r6]<thr); show(f"   skip {lab_}",E,take)
            # skip bottom 20% relative to past preds (causal: threshold = 20% quantile of preds for 2025+ months before)
            take=np.ones(N,bool)
            pr=pf[r6]; mm=M1[r6]; order=np.argsort(mm)
            for a,b in zip(ms[:-1],ms[1:]):
                te=(mm>=a)&(mm<b); past=(mm<a)&~np.isnan(pr)
                if past.sum()<30: continue
                th=np.nanquantile(pr[past],0.2); take[r6[te]]=~(pr[te]<th)
            show("   skip bottom20% (past-pred quantile)",E,take)
