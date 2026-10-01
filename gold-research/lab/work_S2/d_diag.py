from common import *
F=pd.read_pickle("F_S2.pkl"); mo=np.asarray(t.tz_localize(None).to_period("M")).astype(str)
bad=["2025-05","2025-06","2026-03","2026-05","2026-07"]; bad_base=["2025-01","2025-06","2025-11","2026-02","2026-03","2026-07"]
sel=m25; isbad=np.isin(mo,bad)
d=S.dir.values[rows]
tab=pd.DataFrame({"mo":mo[sel],"dir":d[sel],"R1083":Rs[sel,1083],"R0":Rs[sel,0]}).groupby("mo").agg(n=("dir","size"),short_pct=("dir",lambda x:(x<0).mean()*100),R1083=("R1083","mean"),R0=("R0","mean"))
print(tab.round(2).T.to_string())
Z=(F[sel]-F[sel].mean())/F[sel].std()
diff=Z[isbad[sel]].mean()-Z[~isbad[sel]].mean()
print("features most different in losing months (z):"); print(diff.sort_values().head(12).round(2).to_dict()); print(diff.sort_values().tail(12).round(2).to_dict())
for c in ["d1_adx","d1_vol_rank","h4_atr_rank","h1_adx","h4_rng20_atr","d1_ret3","day_rng_atr","dxy_trend","h4_er10","d1_er30","d1_bbw_rank"]:
    print(c, F[sel][isbad[sel]][c].mean().round(2), F[sel][~isbad[sel]][c].mean().round(2))
# shorts vs longs
for j in [0,1083,1041,132]:
    print(j,"long mean",Rs[sel&(d>0),j].mean().round(3),"short mean",Rs[sel&(d<0),j].mean().round(3), (sel&(d<0)).sum())
