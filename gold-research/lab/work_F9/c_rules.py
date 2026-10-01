exec(open('/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_F9/common.py').read())
ch=adaptive_exit()
show('baseline'); show('adaptive exit (ALL, F9)',ch)
y=np.array([R_[i,ch[i]] for i in f9]); kn=np.array([X_[i,ch[i]] for i in f9])
yb=np.asarray(R_[f9,B]); knb=np.asarray(X_[f9,B])
feats=['h1_bbw_rank','h1_dist20','h1_z20','d1_stack','d1_slope50','m5_atr_pct','h1_atr_rank','h1_rsi14','h1_ret12','h4_bbw_rank','m15_ret48','d1_rsi2','d1_ret3','h1_er10','h4_adx','hour','day_rng_atr']
for f in feats:
    x=F[f].values[f9]
    for nb in [2,3,4]:
        tk=online_bin_rule(f9,x,y,kn,nb=nb); T=np.ones(N,bool); T[f9]=tk
        tkb=online_bin_rule(f9,x,yb,knb,nb=nb); Tb=np.ones(N,bool); Tb[f9]=tkb
        m1=lab.evaluate('F9',ch,T)[0]; m0=lab.evaluate('F9',None,Tb)[0]
        print(f"{f:14s} nb={nb} | base-exit: n={m0['n']} sumR={m0['sumR']} PF={m0['PF']} DD={m0['maxDD_R']} mp={m0['months_pos']} | adapt-exit: n={m1['n']} sumR={m1['sumR']} PF={m1['PF']} DD={m1['maxDD_R']} mp={m1['months_pos']} R2={m1['eq_R2']}",flush=True)
