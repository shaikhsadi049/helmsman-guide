exec(open('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/common.py').read())
import json
# sibling check of the squeeze / stretch features, 2025+, under base exit
for sl in ['F8','F10','F11','F9']:
    rows=np.where((S.slot==sl)&(lab.TIME>=lab.D0))[0]; y=np.asarray(R_[rows,B])
    for c in ['h1_bbw_rank','h1_dist20','m5_atr_pct','d1_stack']:
        x=F[c].values[rows]; 
        try: g=pd.Series(y).groupby(pd.qcut(x,3,labels=False,duplicates='drop')).mean().round(2).tolist()
        except Exception as e: g=str(e)
        print(sl,c,g)
# adaptive exit (all candidates, pooled fade history) per fade slot then ML filter on pooled fade with y=adaptive R
chF={}
full=np.full(N,B)
for sl in ['F8','F9','F10','F11']:
    rows=np.where(S.slot==sl)[0]; kn=lab.known_bar(rows,ALL); full[rows]=lab.online_best_policy(rows,ALL,kn)
y=np.array([R_[i,full[i]] for i in fade]); kn=np.array([X_[i,full[i]] for i in fade])
oh=pd.get_dummies(S.slot.values[fade]).astype(float).values
Xf=np.c_[F.values[fade],oh]
pred=lab.online_predict(fade,y,Xf,kn)
prm=dict(objective='binary',learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7)
pc=lab.online_predict(fade,(y>0).astype(float),Xf,kn,params=prm)
P1=np.full(N,np.nan);P1[fade]=pred;P2=np.full(N,np.nan);P2[fade]=pc
res={}
res['baseline']=show('baseline')[0]
m,rr,Rr=show('adaptive exit',full); res['adaptive']=m
for nm,P,q in [('reg<0',P1,0),('cls<0.4',P2,0.4),('cls<0.5',P2,0.5)]:
    T=np.ones(N,bool); T[f9]=~(P[f9]<q); res[nm]=show('adaptive exit + pooled ML(all feats) '+nm,full,T)[0]
    T=np.ones(N,bool); T[f9]=~(P[f9]<q); show('base exit + pooled ML(adaptive y) '+nm,None,T)
# ---- D: monthly diagnosis on baseline trades (all 2025+ signals)
rows=np.where((S.slot=='F9')&(lab.TIME>=lab.D0))[0]; yb=np.asarray(R_[rows,B])
mon=lab.TIME[rows].tz_localize(None).to_period('M')
ms=pd.Series(yb).groupby(mon.values).sum()
bad=ms.index[ms<=0.1]; good=ms.index[ms>0.1]
print('bad months',list(map(str,bad)))
cols=['h1_bbw_rank','h1_dist20','h1_z20','m5_atr_pct','h1_atr_rank','h4_atr_rank','d1_stack','d1_slope50','d1_ret3','h4_adx','h1_adx','h1_er10','h4_er10','day_rng_atr','dxy_trend']
isb=np.isin(mon.values,bad)
D=pd.DataFrame({'bad':F[cols].values[rows][isb].mean(0),'good':F[cols].values[rows][~isb].mean(0)},index=cols)
D['buy_share']=np.nan
print(D.round(3)); print('buy share bad',(S.dir.values[rows][isb]==1).mean().round(2),'good',(S.dir.values[rows][~isb]==1).mean().round(2))
# July 2026 details
j=rows[(mon=='2026-07')]
print(pd.DataFrame({'t':lab.TIME[j],'dir':S.dir.values[j],'R':np.asarray(R_[j,B]).round(2),'R3692':np.asarray(R_[j,3692]).round(2),'bbw':F.h1_bbw_rank.values[j].round(2),'d1stack':F.d1_stack.values[j],'dist20':F.h1_dist20.values[j].round(2)}).to_string())
json.dump({k:{a:(str(b) if not isinstance(b,(int,float)) else b) for a,b in v.items()} for k,v in res.items()},open('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/de_res.json','w'),default=float,indent=1)
