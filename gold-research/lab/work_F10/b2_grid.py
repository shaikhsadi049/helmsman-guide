from common import *
for s in ["F10","F11"]:
    d=pd.read_csv(f"exits_{s}.csv")
    for c in ["sq","tp","be","rat","hm"]: d[c]=[FP[j][c] for j in d.j]
    g=d[(d.be=="none")&(d.rat=="none")]
    print(s); print(g.pivot_table(index=["sq","tp"],columns="hm",values=["sumR","maxDD_R","PF"]).round(2).to_string())
    rows=slot_rows(s)
    cands={"base":73}
    if s=="F10": cands.update({"k70/mean/h1":109,"k70/1R/h0.5":96,"k70/1R/h1":97,"k70/1R/h2":98,"k70/mean/h0.5":108,"k70/f50/h0.5":72,"k70/f50/h2":74})
    else: cands.update({"k70/1R/h2":98,"k70/f70/h2":86,"k50/f30/h2":2,"k70/f30/h2":62,"k70/f50/h2":74,"k70/f30/h1":61,"k90/f30/h2":122})
    for k,j in cands.items():
        rr,R=sim(rows,j); q=pd.Series(R,index=T[rr].tz_localize(None).to_period("Q")).groupby(level=0).sum().round(1)
        print(f"{k:14s}",pname(j),short(met(rr,R)),list(q.values))
