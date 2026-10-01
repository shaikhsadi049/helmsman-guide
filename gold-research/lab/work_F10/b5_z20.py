from common import *
for s in ["F10","F11"]:
    rows=slot_rows(s); L_=li_(rows)
    cs=lj(be="none",rat="none",sq="k70")
    for f in ["h1_z20","m15_ret12","h4_er30","day_rng_atr"]:
        x=F[f].values[rows]; b=pd.qcut(x,3,labels=False)
        t=pd.DataFrame({pname(j)[:12]:RF[L_,j] for j in cs}); t["b"]=b
        g=t.groupby("b").mean().T.round(2); g["n"]=""; print(s,f,"terciles (edges",np.quantile(x,[1/3,2/3]).round(2),")"); print(g.to_string())
