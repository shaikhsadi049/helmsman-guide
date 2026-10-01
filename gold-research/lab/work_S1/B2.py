from h import *
D=pd.read_parquet('B_all.parquet'); D['mp']=D.months_pos.str.split('/').str[0].astype(int)
# pareto front in (sumR up, maxDD down) with mp>=14
c = D[(D.mp>=14)]
front=[]
for _,r in c.sort_values('maxDD_R').iterrows():
    if not front or r.sumR>front[-1].sumR+0.5: front.append(r)
F_=pd.DataFrame(front); F_['name']=[pname(j) for j in F_.j]
print(F_[['j','name','n','PF','sumR','maxDD_R','ret_dd','mp','weeks_pos_pct','eq_R2','ulcer_R','top5']].to_string())
# per quarter of greedy sums for selected
sel=[1200,1248,1254,1320,1280,2004,2036,3204,2284,129,89]
idx=np.where(in25)[0]
for j in sel:
    i,r=run(j); s=pd.Series(r,index=T[i].tz_localize(None)); q=s.groupby(s.index.to_period('Q')).sum().round(1)
    # per-signal quarter means
    qs=pd.Series(R1[idx,j],index=T[idx].tz_localize(None)).groupby(T[idx].tz_localize(None).to_period('Q')).mean().round(2)
    print(j,pname(j),'greedyQ',list(q.values),' sigmeanQ',list(qs.values))
