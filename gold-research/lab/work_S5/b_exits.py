from common import *
P=lab.P[:NP]; b=lab.baseline_policy('S5')
Ri=RS[IN]; q=qtr(T[IN])
mean=Ri.mean(0); med=np.median(Ri,0)
qm=pd.DataFrame(Ri).groupby(np.asarray(q.astype(str))).mean()
qpos=(qm>0).sum(0).values; qmin=qm.min(0).values
# greedy for all 3600 (fast enough?)
import time; t0=time.time()
rows=[]
for j in range(NP):
    i,r=run(j); m=lab.metrics(r,T[i])
    rows.append(dict(j=j,**P[j],mean_all=mean[j],med_all=med[j],q_pos_sig=qpos[j],qmin_sig=qmin[j],**{k:m[k] for k in ['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','q_pos','weeks_pos_pct','eq_R2','ulcer_R','top5days_pct']}))
    if j==20: print('eta',(time.time()-t0)/21*NP)
D=pd.DataFrame(rows); D['mpos']=D.months_pos.str.split('/').str[0].astype(int)
D.to_pickle(W+'/exits_all.pkl')
print(D.loc[b])
