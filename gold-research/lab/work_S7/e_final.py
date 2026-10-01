from common import *
import pickle, json
d=pickle.load(open("shadow2.pkl","rb")); ch,log=d["res"]["small12|ret_ulcer|exp"]; TK=d["TK"]
F=F7()
i,R=run(ch,TK); mrec=lab.metrics(R,T[i]); print("REC",mrec)
ib,Rb=run(BASE); mb=lab.metrics(Rb,T[ib])
print("monthly picks:",list(zip([str(p) for p in lab.MONTHS[:-1].strftime('%Y-%m')],log)))
mon=pd.DataFrame({"base":pd.Series(Rb,index=T[ib].tz_localize(None).to_period("M")).groupby(level=0).sum(),
  "rec":pd.Series(R,index=T[i].tz_localize(None).to_period("M")).groupby(level=0).sum(),
  "rec_n":pd.Series(R,index=T[i].tz_localize(None).to_period("M")).groupby(level=0).size()}).fillna(0)
print(mon.round(1).to_string())
qq=pd.DataFrame({"base":pd.Series(Rb,index=T[ib].tz_localize(None).to_period("Q")).groupby(level=0).sum(),"rec":pd.Series(R,index=T[i].tz_localize(None).to_period("Q")).groupby(level=0).sum()})
print(qq.round(1).to_string())
# drawdown episodes of rec
eq=np.cumsum(R); pk=np.maximum.accumulate(eq); dd=pk-eq; k=dd.argmax(); k0=np.where(eq[:k+1]==pk[k])[0][-1]
print("maxDD from",T[i][k0],"to",T[i][k], "dd",dd[k].round(1))
# top trades
print("top 5 trades R:",np.sort(R)[-5:].round(2), "sum excl top5:", (R.sum()-np.sort(R)[-5:].sum()).round(1))
# hold times
X=X7[i,ch[i]]; print("hold h median/90%:",np.median((X-M[i])/60).round(1),np.quantile((X-M[i])/60,.9).round(1))
# D: diagnosis, signal-level feature means in bad vs good months (all 2025+ signals)
bad=mon.index[mon.rec<0]; print("bad months",list(map(str,bad)))
pm=T.tz_localize(None).to_period("M"); isbad=np.isin(pm.astype(str),[str(b) for b in bad])&IN; isgood=IN&~isbad
FE=["d1_atr_rank","h4_atr_rank","d1_er10","d1_er30","h4_er30","h1_adx","h4_adx","h4_rng20_atr","d1_rng20_atr","day_rng_atr","m5_atr_ratio","vol60_vs_day","d1_ret12","h4_ret12","d1_stack","h4_stack","dxy_trend"]
diag=pd.DataFrame({"bad":F[isbad][FE].mean(),"good":F[isgood][FE].mean(),"std":F[IN][FE].std()}); diag["z_diff"]=(diag.bad-diag.good)/diag["std"]
print(diag.round(3).sort_values("z_diff").to_string())
sigs_per_month=pd.Series(IN,index=pm).groupby(level=0).sum(); print("signals/month bad vs good:", sigs_per_month[sigs_per_month.index.isin(bad)].mean().round(0), sigs_per_month[(~sigs_per_month.index.isin(bad))&(sigs_per_month>0)].mean().round(0))
dirs=lab.SIG.dir.values[rows]; print("rec by dir:", pd.Series(R).groupby(dirs[i]).agg(["size","sum"]).round(1).to_dict())
# portfolio context: other trend slots' baseline monthly
oth={}
for s in ["S1","S2","S3","S4","S5","S6"]:
    m_,rr,Ro=lab.evaluate(s); oth[s]=pd.Series(Ro,index=lab.TIME[rr].tz_localize(None).to_period("M")).groupby(level=0).sum()
O=pd.DataFrame(oth).fillna(0); port=O.sum(1)
print("corr(month) S7 base vs S1-S6 sum:",round(mon.base.corr(port),2)," S7 rec vs S1-S6:",round(mon.rec.corr(port),2))
# daily correlation
pickle.dump(dict(mrec=mrec,mb=mb,mon=mon,qq=qq,diag=diag,port=port),open("final.pkl","wb"))
