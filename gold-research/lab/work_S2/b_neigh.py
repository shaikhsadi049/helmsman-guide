from common import *
G=pd.read_pickle("greedy_all.pkl").set_index("j"); P=lab.P
cols=["n","PF","sumR","maxDD_R","ret_dd","months_pos","eq_R2","top5days_pct","ulcer_R"]
opts=dict(sq=["k50","k70","k90"],tp=["none","f50","1R","2R","3R"],part=["slot","none","half@f30"],be=["none","be1"],trail=["h4q80","h4q50","atr2","atr4","none"],rat=["none","q90k50","q70k50","2R_k50"],ts=["none","ts_half"])
for base in [132,1041,0]:
    print("=== neighbours of",base,P[base]); print("   ",G.loc[base,cols].to_dict())
    for c,vals in opts.items():
        for v in vals:
            if v==P[base][c]: continue
            kw={k:P[base][k] for k in opts}; kw[c]=v; j=lab.policy_index(kind="trend",**kw)[0]
            g=G.loc[j]; print(f"   {c}={v:9s} j={j:4d} n={g.n:3d} sumR={g.sumR:6.1f} DD={g.maxDD_R:4.1f} ret_dd={g.ret_dd:5.1f} mp={g.months_pos} R2={g.eq_R2:.3f} top5={g.top5days_pct} ulcer={g.ulcer_R}")
# quarter table
q=np.asarray(t.tz_localize(None).to_period("Q"))
for j in [0,132,1041,1073,128,124]:
    k,R=run(j); print(j, pd.Series(R).groupby(q[k]).sum().round(1).to_dict())
for j in [0,132,1041]:
    k,R=run(j); mo=np.asarray(t.tz_localize(None).to_period("M"))[k]; print(j, pd.Series(R).groupby(mo).sum().round(1).values)
