from common import *
for s in ["F10","F11"]:
    rows=slot_rows(s); li=np.array([POS[r] for r in rows]); Rm=RF[li]
    q=T[rows].tz_localize(None).to_period("Q")
    out=[]
    for j in range(180):
        rr,R=sim(rows,j); m=met(rr,R)
        qm=pd.Series(Rm[:,j],index=q).groupby(level=0).mean()
        out.append(dict(j=j,pol=pname(j),sig_mean=Rm[:,j].mean(),sig_med=np.median(Rm[:,j]),qpos_sig=(qm>0).sum(),**short(m)))
    d=pd.DataFrame(out); d.to_csv(f"{L}work_F10/exits_{s}.csv",index=False)
    print(s,"baseline",d.loc[BASE].to_dict())
    print(d.sort_values("sumR",ascending=False).head(25).to_string())
    for c in ["sq","tp","be","rat","hm"]:
        d[c]=[FP[j][c] for j in d.j]
        print(d.groupby(c)[["sig_mean","sumR","PF","maxDD_R","eq_R2"]].mean().round(3).to_string())
