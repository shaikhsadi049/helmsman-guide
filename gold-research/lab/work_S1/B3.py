from h import *
F = lab.load_F().iloc[rows].reset_index(drop=True)
idx = np.where(in25)[0]; Q = T[idx].tz_localize(None).to_period("Q").values
# 1) which features predict the gain of no-lock(1320) over lock(1248) and of 2R/rat(2004) over 1248
for a,b in [(1320,1248),(2004,1248),(1280,1200)]:
    d = R1[idx,a]-R1[idx,b]; out=[]
    for c in F.columns:
        x = F[c].values[idx]
        if np.isnan(x).mean()>0.2 or np.nanstd(x)==0: continue
        rk = pd.Series(x).rank(pct=True).values
        hi = rk>0.6; lo = rk<0.4
        qd = [d[(Q==q)&hi].mean()-d[(Q==q)&lo].mean() for q in np.unique(Q)]
        sp = pd.Series(x).corr(pd.Series(d), method="spearman")
        out.append((c, sp, np.sign(qd).tolist().count(np.sign(sp)), np.nanmean(qd)))
    o=pd.DataFrame(out,columns=["f","spear","q_same","hi_lo"]).sort_values("spear",key=abs,ascending=False)
    print(f"--- R[{a}]-R[{b}]  mean diff {d.mean():.3f}"); print(o.head(12).round(3).to_string())
