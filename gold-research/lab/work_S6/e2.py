import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd, json
T=lab.TIME; ch=np.load("rec_choice.npy")
mb,rb,Rb=lab.evaluate("S6"); mr,rr,Rr=lab.evaluate("S6",ch); mi,ri,Ri=lab.evaluate("S6",2280)
def q(rr,R): return pd.Series(R,index=T[rr].tz_localize(None).to_period("Q")).groupby(level=0).sum().round(1)
print(pd.DataFrame({"base":q(rb,Rb),"rec_causal":q(rr,Rr),"IS_2280":q(ri,Ri)}).to_string())
def mo(rr,R): return pd.Series(R,index=T[rr].tz_localize(None).to_period("M")).groupby(level=0).sum()
r3,R3,_=lab.run_slot("S3",2280)
print("monthly corr S6rec vs S3(2280):",round(mo(rr,Rr).corr(mo(r3,R3)),2), " vs S3 baseline:", round(mo(rr,Rr).corr(mo(*lab.run_slot("S3")[:2])),2))
print("weekly corr base S6 vs base S3:", round(pd.Series(Rb,index=T[rb].tz_localize(None).to_period("W")).groupby(level=0).sum().corr(pd.Series(lab.run_slot("S3")[1],index=T[lab.run_slot("S3")[0]].tz_localize(None).to_period("W")).groupby(level=0).sum()),2))
conv=lambda d:{k:(v.item() if hasattr(v,"item") else v) for k,v in d.items()}
json.dump(dict(base=conv(mb),rec=conv(mr),IS=conv(mi)),open("final_metrics.json","w"),indent=1)
print(conv(mb));print(conv(mr));print(conv(mi))
