from common import *
i,r=run(BASE); print(short(met(i,r)))
# check vs lab
m,rr,R=lab.evaluate("S3"); print(short(m))
qq=np.asarray(T.tz_localize(None).to_period("Q").astype(str))
rows=[]
for j in TREND:
    v=RR[IN25,j]; idx,r=run(j); mm=met(idx,r)
    qs=pd.Series(v).groupby(qq[IN25]).mean()
    hold=np.median(XX[IN25,j]-M1[IN25])
    rows.append(dict(j=j,**P[j],sig_mean=v.mean(),sig_med=np.median(v),q_pos_sig=(qs>0).sum(),hold_min=hold,**short(mm)))
df=pd.DataFrame(rows); df.to_pickle("allpol.pkl")
