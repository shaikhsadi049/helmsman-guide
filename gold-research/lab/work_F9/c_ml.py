exec(open('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/common.py').read())
pre=f9[lab.TIME[f9]<lab.D0]; print('warmup F9 n',len(pre),'mean R base',np.asarray(R_[pre,B]).mean().round(3), 'k70f70be1hm2',np.asarray(R_[pre,3692]).mean().round(3))
for sl in ['F8','F10','F11']:
    p=np.where((S.slot==sl)&(lab.TIME<lab.D0))[0]; print(sl,'warmup',len(p),np.asarray(R_[p,B]).mean().round(3))
ch_f9=adaptive_exit()
show('baseline'); show('adaptive exit',ch_f9)
# pooled ML: target = R under base exit and under 3692; features + slot one-hot
slots=['F8','F9','F10','F11']
oh=pd.get_dummies(S.slot.values[fade]).astype(float).values
sets={'all':list(F.columns),
 'core':['h1_bbw_rank','h1_dist20','h1_z20','h1_rsi14','h1_ret12','m5_atr_pct','m15_atr_pct','d1_stack','d1_slope50','d1_rsi2','d1_ret3','h4_bbw_rank','h1_er10','h4_adx','hour','day_rng_atr','dxy_trend'],
 'h1d1':[c for c in F.columns if c.startswith(('h1_','d1_','h4_'))]}
for J,nmJ in [(B,'base'),(3692,'k70f70be1hm2')]:
    y=np.asarray(R_[fade,J]); kn=np.asarray(X_[fade,J])
    for sn,cols in sets.items():
        for pool in ['fade','F9']:
            rows=fade if pool=='fade' else f9
            Xf=F[cols].values[rows]
            if pool=='fade': Xf=np.c_[Xf,oh]
            yy=np.asarray(R_[rows,J]); kk=np.asarray(X_[rows,J])
            for tgt in ['reg','cls']:
                if tgt=='reg': pred=lab.online_predict(rows,yy,Xf,kk,min_train=60 if pool=='F9' else 120); thr=0
                else:
                    prm=dict(objective='binary',learning_rate=0.03,num_leaves=8,min_data_in_leaf=25,feature_fraction=0.5,bagging_fraction=0.8,bagging_freq=1,lambda_l2=5.0,verbose=-1,num_threads=1,seed=7)
                    pred=lab.online_predict(rows,(yy>0).astype(float),Xf,kk,min_train=60 if pool=='F9' else 120,params=prm); thr=None
                full=np.full(N,np.nan); full[rows]=pred
                p9=full[f9]; v=~np.isnan(p9)&(lab.TIME[f9]>=lab.D0)
                ic=pd.Series(p9[v]).corr(pd.Series(np.asarray(R_[f9,J])[v]),method='spearman')
                for q in ([0] if tgt=='reg' else [0.4,0.5]):
                    T=np.ones(N,bool); T[f9]=~(p9<q)
                    chs=None if J==B else J
                    m=lab.evaluate('F9',chs,T)[0]
                    print(f"y={nmJ:13s} {sn:5s} pool={pool:4s} {tgt} thr={q} IC={ic:+.3f} | n={m['n']} sumR={m['sumR']} PF={m['PF']} DD={m['maxDD_R']} mp={m['months_pos']} R2={m['eq_R2']} ulcer={m['ulcer_R']}",flush=True)
