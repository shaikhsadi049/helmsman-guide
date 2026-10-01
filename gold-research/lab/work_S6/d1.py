import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd
S=lab.SIG; R_=lab.load_R(); F=lab.load_F(); N=len(S); T=lab.TIME
r6=np.where((S.slot.values=="S6")&(T>=lab.D0))[0]; r3=np.where((S.slot.values=="S3")&(T>=lab.D0))[0]
m6=set(S.m1.values[r6]); only3=r3[~np.isin(S.m1.values[r3],list(m6))]; in3=r3[np.isin(S.m1.values[r3],list(m6))]
for E in [1208,2280,lab.baseline_policy("S3")]:
    print("exit",E,"S6 sig meanR %.3f (n=%d) | S3 sigs also S6 %.3f | S3-only (RSI 5-10) %.3f (n=%d)"%(
        np.nanmean(R_[r6,E]),len(r6),np.nanmean(R_[in3,E]),np.nanmean(R_[only3,E]),len(only3)))
# taken-trade overlap baseline
rr6,_,_=lab.run_slot("S6"); rr3,R3,_=lab.run_slot("S3")
print("S6 taken",len(rr6),"of which same m1 taken by S3:",np.isin(S.m1.values[rr6],S.m1.values[rr3]).mean())
for E in [2280]:
    rr6,_,_=lab.run_slot("S6",E); rr3,_,_=lab.run_slot("S3",E)
    print("exit 2280: S6 taken",len(rr6),"same m1 taken by S3:",np.isin(S.m1.values[rr6],S.m1.values[rr3]).mean())
    m3=lab.metrics(*[lab.run_slot("S3",E)[1],T[lab.run_slot("S3",E)[0]]]); print("S3 under 2280:",m3)
    print("S3 baseline:",lab.evaluate("S3")[0])
# monthly comparison
def mon(rr,R): return pd.Series(R,index=T[rr].tz_localize(None).to_period("M")).groupby(level=0).sum()
rb,Rb,_=lab.run_slot("S6"); re,Re,_=lab.run_slot("S6",2280)
M=pd.DataFrame({"base_n":pd.Series(1,index=T[rb].tz_localize(None).to_period("M")).groupby(level=0).sum(),"base_R":mon(rb,Rb),
   "rec_n":pd.Series(1,index=T[re].tz_localize(None).to_period("M")).groupby(level=0).sum(),"rec_R":mon(re,Re)}).fillna(0)
# all-signal mean per month
allm=pd.Series(np.asarray(R_[r6,2280]),index=T[r6].tz_localize(None).to_period("M")).groupby(level=0).agg(["count","mean"])
M["sig_n"]=allm["count"]; M["sig_meanR_2280"]=allm["mean"]
print(M.round(2).to_string()); M.to_pickle("monthly.pkl")
# D: features in losing/flat months vs good months (rec exit) using all signals in month
bad=M.index[M.rec_R<=0.5]; print("weak months:",list(bad.astype(str)))
fm=F.iloc[r6].copy(); fm["mon"]=T[r6].tz_localize(None).to_period("M"); fm["bad"]=fm.mon.isin(bad)
z=(fm.groupby("bad").mean(numeric_only=True).T); sd=fm.std(numeric_only=True)
z["d_sd"]=(z[True]-z[False])/sd; z=z.dropna().sort_values("d_sd")
print(z.head(12).round(3)); print(z.tail(12).round(3))
