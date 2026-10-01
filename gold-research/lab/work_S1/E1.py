from h import *
D=pd.read_parquet('B_all.parquet')
c=['j','sq','tp','part','be','trail','rat','ts','n','PF','sumR','maxDD_R','ret_dd','months_pos','weeks_pos_pct','eq_R2','ulcer_R','top5']
print(D[(D.sq=='k70')&(D.tp=='none')&(D.part=='none')&(D.ts=='none')&D.trail.isin(['h4q80','h4q50'])][c].to_string())
def blend(a,b,w=0.5):
    r = w*R1[:,a]+(1-w)*R1[:,b]; x = np.maximum(X1[:,a],X1[:,b])
    idx=np.where(in25)[0]; tk=greedy(idx,x[idx]); ii=idx[tk]; return ii, r[ii]
for a,b in [(1248,1320),(1254,1320),(1200,1320),(1254,1328),(1248,1280),(1254,1324)]:
    for w in (0.5,):
        ii,r=blend(a,b,w); m=lab.metrics(r,T[ii]); s=pd.Series(r,index=T[ii].tz_localize(None)); q=s.groupby(s.index.to_period('Q')).sum().round(1).tolist()
        print(a,b,w,fmt(m),q)
for j in (1200,1248,1254,1320):
    i,r=run(j); s=pd.Series(r,index=T[i].tz_localize(None)); print(j, s.groupby(s.index.to_period('Q')).sum().round(1).tolist())
