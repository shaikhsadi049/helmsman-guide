from h import *
F = lab.load_F().iloc[rows].reset_index(drop=True)
idx = np.where(in25)[0]; Q = T[idx].tz_localize(None).to_period("Q").values; uq=np.unique(Q)
for EX in (1248, 1320):
    y = R1[idx, EX]; L = (y < 0).astype(float); out=[]
    for c in F.columns:
        x = F[c].values[idx]
        if np.isnan(x).mean()>0.2 or np.nanstd(x)==0: continue
        r = pd.Series(x).rank(pct=True).values
        qb = np.minimum((r*5).astype(int),4)
        qm = [y[qb==k].mean() for k in range(5)]
        hi=r>0.5
        qd=np.array([y[(Q==q)&hi].mean()-y[(Q==q)&~hi].mean() if ((Q==q)&hi).sum()>3 and ((Q==q)&~hi).sum()>3 else np.nan for q in uq])
        sp = pd.Series(x).corr(pd.Series(y), method="spearman")
        out.append(dict(f=c, spear=sp, q_same=int(np.nansum(np.sign(qd)==np.sign(sp))), nq=int((~np.isnan(qd)).sum()), Q1=qm[0],Q2=qm[1],Q3=qm[2],Q4=qm[3],Q5=qm[4], loss_spear=pd.Series(x).corr(pd.Series(L),method="spearman")))
    o=pd.DataFrame(out).sort_values("spear",key=abs,ascending=False)
    o.to_csv(f"C1_{EX}.csv")
    print(f"=== exit {EX}  mean {y.mean():.3f}  loss rate {L.mean():.2f}"); print(o.head(25).round(3).to_string())
