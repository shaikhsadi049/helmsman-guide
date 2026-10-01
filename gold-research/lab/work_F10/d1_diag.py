from common import *
import itertools, warnings; warnings.filterwarnings("ignore")
print("cross-slot: k70/h1 mean vs f50 target, 2025+ greedy")
for s in ["F8","F9","F10","F11"]:
    rows=slot_rows(s)
    print(s,{pname(j)[:9]:short(met(*sim(rows,j)))["sumR"] for j in [73,109,97,61,85,96]})
for s,ex in [("F10",109),("F11",73)]:
    rows=slot_rows(s); rr,R=sim(rows,ex)
    mon=pd.Series(R,index=T[rr].tz_localize(None).to_period("M"))
    ms=mon.groupby(level=0).sum(); bad=ms[ms<0].index
    Fm=F.iloc[rr].copy(); Fm["bad"]=mon.index.isin(bad); Fm["R"]=R
    z=(Fm[Fm.bad].mean()-Fm[~Fm.bad].mean())/Fm.std()
    print(f"\n{s} exit {pname(ex)} losing months:",list(map(str,bad)),"trades in them",Fm.bad.sum(),"sumR",round(R[Fm.bad].sum(),1))
    print(z.drop(["bad","R"]).sort_values().round(2).iloc[list(range(8))+list(range(-8,0))].to_string())
    # losers: trade level
    print("trade-level loss share: stops (R<-0.8)",(R<-0.8).sum(),"of",len(R),"; time exits small",( (R>-0.8)&(R<0)).sum())
    # pairs
    ys=RF[li_(rows),ex]; top=pd.read_csv(f"uni_{s}.csv").f.head(10).tolist()+["h4_er30"]
    q=T[rows].tz_localize(None).to_period("Q").astype(str).values
    pr=[]
    for a,b in itertools.combinations(dict.fromkeys(top),2):
        xa=F[a].values[rows]>np.median(F[a].values[rows]); xb=F[b].values[rows]>np.median(F[b].values[rows])
        for ca in (0,1):
            for cb in (0,1):
                sel=(xa==ca)&(xb==cb)
                if sel.sum()<15: continue
                cons=sum(ys[sel&(q==k)].mean()<ys[~sel&(q==k)].mean() for k in np.unique(q) if (sel&(q==k)).sum()>1)
                pr.append((a,ca,b,cb,sel.sum(),round(ys[sel].mean(),3),round(ys[~sel].mean(),3),cons))
    d=pd.DataFrame(pr,columns=["a","a_hi","b","b_hi","n","mean_cell","mean_rest","q_worse"]).sort_values("mean_cell")
    print(d.head(6).to_string())
