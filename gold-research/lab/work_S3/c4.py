from common import *
exec(open("c3.py").read().split("for pol in [2168,1208]:")[0])  # reuse ev, online_rule
for pol in [2168,1208]:
    for f in ["d1_atr_rank","d1_ribbon","h4_vr10","d1_atr_ratio","d1_bbw_rank","h4_atr_pct","d1_adx"]:
        for side in ["lo"]:
            for qc in [0.2,0.33]: ev(online_rule(f,pol,side,qc),f"{f} {side} q{qc}",pol)
    # equity-curve (shadow) filter: mean of last N known shadow outcomes under pol
    y=RR[:,pol]; x=XX[:,pol]
    order=np.argsort(x)  # by exit bar
    xs=x[order]; ys=y[order]
    for N in [10,20,40,80]:
        for thr in [0.0, -0.1]:
            skip=np.zeros(len(ROWS),bool)
            for k in range(len(ROWS)):
                nk=np.searchsorted(xs,M1[k])   # outcomes known before signal
                if nk>=N: skip[k]=ys[nk-N:nk].mean()<thr
            ev(skip,f"shadow-equity last{N} mean<{thr}",pol)
df=pd.DataFrame(res); pd.set_option('display.width',250); print(df.sort_values(["pol","sumR"],ascending=False).to_string())
