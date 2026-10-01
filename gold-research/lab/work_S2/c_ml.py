from common import *
import time
Fall=lab.load_F(); Rall=lab.load_R(); Xall=lab.load_X()
F=pd.read_pickle("F_S2.pkl")
ext=["h1_adx","h1_slope50","h1_ribbon","h4_rng20_atr","d1_ret3","m15_dist200","h4_ret12","d1_bar_atr","h1_ret48","h4_rsi14","h4_di","h1_rng20_atr","d1_streak","prev_rng_atr","d1_vol_rank","m15_atr_pct","h4_atr_rank","d1_adx"]
def keep(pol,take): m=met(pol,take); return {k:m[k] for k in ["n","PF","sumR","maxDD_R","ret_dd","months_pos","eq_R2","top5days_pct","ulcer_R"]}
res={}
for pol in [0,1041,132]:
    y=Rs[:,pol]; known=Xs[:,pol]
    print("== pol",pol,"no filter",keep(pol,None))
    for nm,cols in [("all",list(F.columns)),("ext18",ext)]:
        for tgt in ["R","win"]:
            yy=y if tgt=="R" else (y>0).astype(float)
            t0=time.time()
            pr=lab.online_predict(rows,yy,F[cols],known,min_train=120)
            thr=0 if tgt=="R" else np.nan
            v=m25&~np.isnan(pr); ic=pd.Series(pr[v]).corr(pd.Series(y[v]),method="spearman")
            for cut in ([0,-0.2,0.2] if tgt=="R" else [0.3,0.4,0.5]):
                take=~(pr<cut)
                print(f"  S2-only {nm} {tgt} cut{cut} IC={ic:.3f} skip%={100*(~take[m25]).mean():.0f}",keep(pol,take),f"{time.time()-t0:.0f}s")
            np.save(f"pred_{pol}_{nm}_{tgt}.npy",pr)
    # pooled with sibling trend slots
    trows=np.where((lab.SIG.kind.values=="trend"))[0]
    yp=np.asarray(Rall[trows,pol]); kp=np.asarray(Xall[trows,pol])
    Fp=Fall.iloc[trows][ext].copy(); Fp["is_s2"]=(lab.SIG.slot.values[trows]=="S2").astype(float)
    for s in ["S1","S3","S4","S5","S6","S7"]: Fp["is_"+s]=(lab.SIG.slot.values[trows]==s).astype(float)
    t0=time.time(); pp=lab.online_predict(trows,yp,Fp,kp,min_train=300)
    pos=np.searchsorted(trows,rows); pr=pp[pos]
    v=m25&~np.isnan(pr); ic=pd.Series(pr[v]).corr(pd.Series(y[v]),method="spearman")
    for cut in [0,-0.2,0.2]:
        take=~(pr<cut); print(f"  POOLED ext18 R cut{cut} IC={ic:.3f} skip%={100*(~take[m25]).mean():.0f}",keep(pol,take),f"{time.time()-t0:.0f}s")
    np.save(f"pred_{pol}_pooled.npy",pr)
