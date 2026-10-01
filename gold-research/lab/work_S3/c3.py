from common import *
F=getF(); res=[]
def ev(skip,label,pol):
    i,r=run(pol,~skip); m=short(met(i,r)); m.update(label=label,pol=pol,skip=round(skip[IN25].mean()*100,1)); res.append(m)
def online_rule(f,pol,side,qcut=0.2,thr=0.0):
    x=F[f].values; y=RR[:,pol]; kn=XX[:,pol]; skip=np.zeros(len(ROWS),bool)
    for a,b in zip(MS[:-1],MS[1:]):
        te=(M1>=a)&(M1<b); tr=kn<a
        if tr.sum()<100: continue
        e=np.nanquantile(x[tr], qcut if side=="lo" else 1-qcut)
        sel=tr&((x<e) if side=="lo" else (x>e))
        if y[sel].mean()<thr: skip[te]=(x[te]<e) if side=="lo" else (x[te]>e)
    return skip
for pol in [2168,1208]:
    for f in ["day_rng_atr","m15_vr10","m15_er30","h1_rngpos20","day_pos","m15_bar_atr","h1_adx","h4_adx","dxy_z20","h4_atr_rank","m5_atr_pct","h1_atr_pct","d1_vol_ratio"]:
        for side in ["lo","hi"]:
            for qc in [0.2,0.33]:
                ev(online_rule(f,pol,side,qc),f"{f} {side} q{qc}",pol)
    # auto: per month choose the single feature/side whose past bottom-bucket mean is most negative relative to overall, require < 0
    y=RR[:,pol]; kn=XX[:,pol]; skip=np.zeros(len(ROWS),bool); picks=[]
    Xa=F.values
    for a,b in zip(MS[:-1],MS[1:]):
        te=(M1>=a)&(M1<b); tr=kn<a; best=(0,None)
        for c in range(Xa.shape[1]):
            x=Xa[:,c]
            for side in ["lo","hi"]:
                e=np.nanquantile(x[tr],0.2 if side=="lo" else 0.8); sel=tr&((x<e) if side=="lo" else (x>e))
                if sel.sum()<40: continue
                mu=y[sel].mean()
                if mu<best[0]: best=(mu,(c,side,e))
        if best[1]:
            c,side,e=best[1]; x=Xa[:,c]; skip[te]=(x[te]<e) if side=="lo" else (x[te]>e); picks.append(F.columns[c]+side)
        else: picks.append(None)
    ev(skip,"AUTO best single feature cut",pol); print(pol,"auto picks",picks)
df=pd.DataFrame(res); pd.set_option('display.width',250)
for pol in [2168,1208]:
    print(df[df.pol==pol].sort_values("sumR",ascending=False).to_string())
df.to_pickle("c3.pkl")
