import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd
S=lab.SIG; R_=lab.load_R(); X_=lab.load_X(); F=lab.load_F(); N=len(S); ms=lab._ms(); M1=S.m1.values; T=lab.TIME
r6=np.where(S.slot.values=="S6")[0]; r3=np.where(S.slot.values=="S3")[0]; pool=np.r_[r6,r3]; base=lab.baseline_policy("S6")
K=("n","PF","sumR","maxDD_R","months_pos","q_pos","top5days_pct","eq_R2","ulcer_R")
G=pd.read_pickle("greedy_all.pkl")
print("neighbourhood of 2280 (k?/tp?/part?/be1/h4q80/rat none/ts none):")
sel=G[(G.be=="be1")&(G.trail=="h4q80")&(G.rat=="none")&(G.ts=="none")&(G.sq.isin(["k50","k70","k90"]))]
print(sel[["sq","tp","part","n","PF","sumR","maxDD_R","months_pos","top5days_pct","eq_R2"]].sort_values(["tp","part","sq"]).to_string())
print("2280 variants on trail/rat/ts:")
v=G[(G.sq=="k70")&(G.tp=="3R")&(G.part=="none")]
print(v[["be","trail","rat","ts","n","PF","sumR","maxDD_R","months_pos","top5days_pct","eq_R2"]].to_string())
def chooser(trr,cands,crit="clip3"):
    Rm=np.asarray(R_[trr][:,cands]).astype(float); known=np.asarray(X_[trr][:,cands]).max(1)
    choice=np.full(N,base); picks=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=r6[(M1[r6]>=a)&(M1[r6]<b)]; tr=known<a
        if len(te)==0 or tr.sum()<30: continue
        X=Rm[tr]; s=np.nanmean(np.minimum(X,3),0) if crit=="clip3" else np.nanmean(X,0)/np.nanstd(X,0)
        c=cands[int(np.nanargmax(s))]; choice[te]=c; picks.append(c)
    return choice,picks
grid=[base]+[lab.policy_index(kind="trend",sq=sq,tp=tp,part=pt,be="be1",trail="h4q80",rat="none",ts="none")[0]
      for sq in ["k70","k90"] for tp in ["2R","3R","none"] for pt in ["none","half@f30","slot"]]
for nm,trr in [("S6",r6),("pool",pool)]:
    for crit in ["clip3","sharpe"]:
        ch,pk=chooser(trr,grid,crit); m,rr,R=lab.evaluate("S6",ch)
        print(f"grid19 {nm} {crit}",{k:m[k] for k in K},pd.Series(pk).value_counts().to_dict())
        if nm=="pool" and crit=="clip3": np.save("rec_choice.npy",ch)
# be1-only full family causal
be1=[j for j in range(3600) if lab.P[j]["be"]=="be1"]
ch,pk=chooser(pool,be1,"clip3"); m,rr,R=lab.evaluate("S6",ch); print("all be1 policies pool clip3",{k:m[k] for k in K},pd.Series(pk).value_counts().to_dict())
# post-hoc regime rules from D
E=2280; y=np.asarray(R_[:,E]).astype(float); known=lab.known_bar(pool,[E])
for f in ["d1_dist200","dxy_trend","d1_rng20_atr"]:
    x=F[f].values; take=np.ones(N,bool)
    for a,b in zip(ms[:-1],ms[1:]):
        te=r6[(M1[r6]>=a)&(M1[r6]<b)]; tr=pool[known<a]
        if len(te)==0 or len(tr)<100: continue
        ed=np.nanquantile(x[tr],[.2,.4,.6,.8]); bt=np.searchsorted(ed,x[tr]); mu_all=np.nanmean(y[tr])
        mu=np.array([(y[tr][bt==k].sum()+20*mu_all)/((bt==k).sum()+20) for k in range(5)])
        take[te]=~np.isin(np.searchsorted(ed,x[te]),np.where(mu<0)[0])
    m,_,_=lab.evaluate("S6",E,take); print("rule pool",f,{k:m[k] for k in K})
