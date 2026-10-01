import sys, json; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
S=lab.SIG; F=lab.load_F(); R_=lab.load_R()
def pid(sq,tp,hm=1.0): return lab.policy_index(kind='fade',sq=sq,tp=tp,be='none',rat='none',hm=hm)[0]
rows=np.where(S.slot=='F8')[0]; r25=rows[lab.TIME[rows]>=lab.D0]
q=lab.TIME[r25].tz_localize(None).to_period('Q')
for tp in ['f30','f50','f70','1R']:
    d=pd.Series(np.asarray(R_[r25,pid('k50',tp)])-np.asarray(R_[r25,pid('k70',tp)])).groupby(q.values).mean()
    print('k50-k70',tp,d.round(3).to_dict())
C=[pid(s,'f50') for s in ['k50','k70','k90']]
kn=lab.known_bar(rows,C); ch=lab.online_best_policy(rows,C,kn)
full=np.full(len(S),lab.baseline_policy('F8')); full[rows]=ch
mo=lab.TIME[rows].tz_localize(None).to_period('M')
print(pd.Series(ch).map(lambda j:lab.P[j]['sq']).groupby(mo.values).agg(lambda s:s.value_counts().to_dict()).to_string())
mr,rr,R=lab.evaluate('F8',full); print('REC',mr)
mb,rb,Rb=lab.evaluate('F8'); mi,ri,Ri=lab.evaluate('F8',pid('k50','f50'))
T=pd.DataFrame({'base':pd.Series(Rb,index=lab.TIME[rb].tz_localize(None).to_period('M')).groupby(level=0).sum(),
                'rec':pd.Series(R,index=lab.TIME[rr].tz_localize(None).to_period('M')).groupby(level=0).sum(),
                'k50f50':pd.Series(Ri,index=lab.TIME[ri].tz_localize(None).to_period('M')).groupby(level=0).sum()}).round(2)
print(T.to_string())
# cost stress on recommended
st=np.array([S[lab.P[j]['sq']].values[i]*S.atr.values[i] for i,j in zip(rr,full[rr])])
for ex in [0.34,0.68]:
    print('REC cost+',ex,lab.metrics(R-ex/st,lab.TIME[rr]))
# exploratory gate: d1_adx & d1_atr_ratio high (causal past-80pct thresholds)
ms=lab._ms(); m1=lab.M1[rows]; y=np.asarray(R_[rows,pid('k50','f50')]); kn1=np.asarray(lab.load_X()[rows,pid('k50','f50')])
x1=F.d1_adx.values[rows]; x2=F.d1_atr_ratio.values[rows]; take=np.ones(len(rows),bool)
for a,b in zip(ms[:-1],ms[1:]):
    te=(m1>=a)&(m1<b); tr=kn1<a
    if not te.any(): continue
    t1=np.nanquantile(x1[tr],0.7); t2=np.nanquantile(x2[tr],0.7)
    take[te&(x1>t1)&(x2>t2)]=False
tm=np.ones(len(S),bool); tm[rows]=take
print('gate skip%',round(100*(1-take[lab.TIME[rows]>=lab.D0].mean())),'rec+gate',lab.evaluate('F8',full,tm)[0])
post=lab.TIME[rows]>=lab.D0
print('gated-out signals mean R k50f50',y[post&~take].mean().round(3),'n',(post&~take).sum(),'kept',y[post&take].mean().round(3))
json.dump(dict(baseline=mb,recommended=mr,in_sample_best=mi,monthly=T.reset_index().astype(str).to_dict('records')),open('final_metrics.json','w'),default=float,indent=1)
