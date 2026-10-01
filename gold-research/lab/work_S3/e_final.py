from common import *
import json
def tojs(m): return {k:(float(v) if isinstance(v,(np.floating,float)) else (int(v) if isinstance(v,(np.integer,)) else v)) for k,v in m.items()}
# causal recommended: online chooser over {base, 3R} by R-per-time-in-market objective
cands=[1208,2168]; ch=online_choose(cands,obj="rate")
print("causal picks", pd.Series(ch[IN25]).value_counts().to_dict())
i,r=run(ch); mrec=met(i,r)
ib,rb=run(1208); mb=met(ib,rb)
ii,ri=run(2369); mis=met(ii,ri)
# full lab check
mlab,_,_=lab.evaluate("S3", np.full(len(lab.SIG),2168)); print("lab.evaluate 2168", short(mlab))
tab=pd.DataFrame({"baseline_1208":monthly(ib,rb),"rec_2168":monthly(i,r),"IS_best_2369":monthly(ii,ri),"alt_2288":monthly(*run(2288)),"nb_3128":monthly(*run(3128))}).round(1)
tab["n_base"]=pd.Series(1,index=T[ib].tz_localize(None).to_period("M")).groupby(level=0).sum(); tab["n_rec"]=pd.Series(1,index=T[i].tz_localize(None).to_period("M")).groupby(level=0).sum()
print(tab.fillna(0).to_string())
alts={"alt_2288_k70_3R_nopart_be1 (causal mean-chooser pick)":met(*run(2288)),"nb_3128_k90_2R_slot":met(*run(3128)),"nb_1928_k70_2R_slot":met(*run(1928)),"causal_chooser_k70slot_tp{none,f50,1R,2R,3R}_rate":met(*run(online_choose([1208,2168,1928,1688,1448],obj='rate'))),
      "causal_chooser_k70slot_tp_mean":met(*run(online_choose([1208,2168,1928,1688,1448],obj='mean')))}
for k,m in alts.items(): print(k, short(m))
json.dump(dict(baseline=tojs(mb),recommended=tojs(mrec),in_sample_best=tojs(mis),alts={k:tojs(v) for k,v in alts.items()}),open("final_metrics.json","w"),indent=1)
