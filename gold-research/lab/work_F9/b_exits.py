import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab"); import lab, numpy as np, pandas as pd
S=lab.SIG; R_=lab.load_R()
rows=np.where((S.slot=='F9')&(lab.TIME>=lab.D0))[0]
J=list(range(3600,3780)); Rm=np.asarray(R_[rows][:,J])
q=lab.TIME[rows].tz_localize(None).to_period('Q')
out=[]
for k,j in enumerate(J):
    r=Rm[:,k]; qs=pd.Series(r).groupby(q.values).mean()
    out.append(dict(j=j,**{a:b for a,b in lab.P[j].items() if a!='kind'},mean=r.mean(),med=np.median(r),qpos=(qs>0).sum(),qmin=qs.min()))
D=pd.DataFrame(out).sort_values('mean',ascending=False)
pd.set_option('display.width',200)
print(D.head(25).round(3)); print(D.tail(5).round(3))
b=lab.baseline_policy('F9'); print('base rank',list(D.j).index(b)+1, D[D.j==b].round(3))
for c in ['sq','tp','be','rat','hm']: print(D.groupby(c)[['mean','qpos']].mean().round(3))
# run_slot top 50 + base
res=[]
for j in list(D.j[:50])+[b]:
    rr,R,X=lab.run_slot('F9',j); m=lab.metrics(R,lab.TIME[rr]); res.append(dict(j=j,**lab.P[j],**m))
E=pd.DataFrame(res).drop(columns='kind').sort_values('sumR',ascending=False)
print(E[['j','sq','tp','be','rat','hm','n','win','PF','sumR','maxDD_R','months_pos','q_pos','eq_R2','ulcer_R']].to_string())
E.to_csv('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/exits_top50.csv')
D.to_csv('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/exits_all.csv')
