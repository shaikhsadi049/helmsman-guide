from common import *
import warnings; warnings.filterwarnings("ignore")
exec(open("e1_final.py").read().split("out={}")[0])
res=[]
for s,ex in [("F10",109),("F11",73)]:
    rows=np.where(S.slot.values==s)[0]; rows=rows[np.argsort(M1[rows])]; tgt=T[rows]>=lab.D0
    y=RF[li_(rows),ex]; kn=XF[li_(rows),ex]
    for f in F.columns:
        for side in ["low","high"]:
            x=F[f].values[rows]*(1 if side=="low" else -1)
            if np.nanstd(x)==0: continue
            sk,act=gated_skip(rows,y,kn,x,0.25)
            rr,R=sim(rows[tgt],ex,~sk[tgt]); m=met(rr,R)
            res.append(dict(slot=s,f=f,side=side,act=sum(act),sumR=m["sumR"],PF=m["PF"],dd=m["maxDD_R"]))
d=pd.DataFrame(res); d.to_csv("scan_gated.csv",index=False)
for s in ["F10","F11"]:
    e=d[d.slot==s]; print(s,"n rules",len(e),"sumR quantiles",e.sumR.quantile([.05,.25,.5,.75,.95]).round(1).to_dict())
    print(e.sort_values("sumR",ascending=False).head(12).to_string())
    print("h4_er30:",e[e.f=="h4_er30"].to_string())
# cross-slot: rules that help both
p=d.pivot_table(index=["f","side"],columns="slot",values="sumR"); p["both"]=(p.F10>16.2)&(p.F11>5.6)
print("helps both:",p.both.sum(),"of",len(p)); print(p[p.both].sort_values("F11",ascending=False).head(15).to_string())
