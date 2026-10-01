from h import *
import json
def blend(a,b,w=0.5):
    r = w*R1[:,a]+(1-w)*R1[:,b]; x = np.maximum(X1[:,a],X1[:,b])
    idx=np.where(in25)[0]; tk=greedy(idx,x[idx]); ii=idx[tk]; return ii, r[ii]
i0,r0=run(BASE); i1,r1=blend(1200,1320)
s0=pd.Series(r0,index=T[i0].tz_localize(None).to_period('M')).groupby(level=0).sum()
s1=pd.Series(r1,index=T[i1].tz_localize(None).to_period('M')).groupby(level=0).sum()
mt=pd.DataFrame({"base":s0,"rec":s1}).fillna(0); mt["diff"]=mt.rec-mt.base; print(mt.round(2).to_string()); print("months rec>=base", (mt['diff']>=-0.01).sum(), "/", len(mt))
for nm,(ii,rr) in {"base":(i0,r0),"rec":(i1,r1)}.items():
    m=T[ii].tz_localize(None).to_period('M'); k=(m!=pd.Period('2026-01','M'))
    print(nm,"ex-Jan2026", fmt(lab.metrics(rr[k],T[ii][k])))
    print(nm,"largest trade", rr.max().round(2), "sum ex top trade", (rr.sum()-rr.max()).round(1))
mb=lab.metrics(r0,T[i0]); mr=lab.metrics(r1,T[i1]); mi=met(1248)
J=dict(base=mb,rec=mr,isb=mi)
json.dump(J,open("final_metrics.json","w"),default=float,indent=1)
print(mr)
