import sys; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd
R_=lab.load_R()
rows=np.where((lab.SIG.slot=='F8')&(lab.TIME>=lab.D0))[0]
fp=[j for j,p in enumerate(lab.P) if p['kind']=='fade']
qt=lab.TIME[rows].tz_localize(None).to_period('Q')
out=[]
for j in fp:
    r=np.asarray(R_[rows,j]); qm=pd.Series(r).groupby(qt.values).mean()
    rr,R,X=lab.run_slot('F8',j); m=lab.metrics(R,lab.TIME[rr])
    out.append(dict(j=j,**{k:v for k,v in lab.P[j].items() if k!='kind'},allmean=r.mean(),allmed=np.median(r),qpos_all=(qm>0).sum(),**m))
D=pd.DataFrame(out); D.to_csv('b_all.csv',index=False)
pd.set_option('display.width',250)
cols=['j','sq','tp','be','rat','hm','allmean','qpos_all','n','win','PF','sumR','maxDD_R','ret_dd','months_pos','q_pos','eq_R2','ulcer_R']
print(D.sort_values('ret_dd',ascending=False)[cols].head(30).round(3).to_string())
print(D[D.j==3673][cols])
for c in ['sq','tp','be','rat','hm']:
    print(D.groupby(c)[['allmean','sumR','ret_dd','eq_R2']].mean().round(3))
