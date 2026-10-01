import sys; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd, json
S=lab.SIG; F=lab.load_F(); R_=lab.load_R()
rows=np.where(S.slot=='F8')[0]
def pid(sq,tp,hm=1.0): return lab.policy_index(kind='fade',sq=sq,tp=tp,be='none',rat='none',hm=hm)[0]
C=[pid(s,t) for s in ['k50','k70','k90'] for t in ['f30','f50','f70','1R']]
C2=C+[pid(s,t,2.0) for s in ['k50','k70','k90'] for t in ['f30','f50','f70','1R']]
def full(ch):
    a=np.full(len(S),lab.baseline_policy('F8')); a[rows]=ch; return a
res={}
for name,cands in [('C12',C),('C24',C2),('sq_f50',[pid(s,'f50') for s in ['k50','k70','k90']])]:
    known=lab.known_bar(rows,cands)
    ch=lab.online_best_policy(rows,cands,known)
    m,rr,R=lab.evaluate('F8',full(ch)); res[(name,'none')]=m
    sel=pd.Series(ch[lab.TIME[rows]>=lab.D0]).map(lambda j: f"{lab.P[j]['sq']}/{lab.P[j]['tp']}/{lab.P[j]['hm']}").value_counts().to_dict()
    print(name,'fixed-causal',m,sel)
    if name!='C12': continue
    for reg in ['m15_atr_rank','h1_atr_rank','h4_adx','d1_er10','h4_er10','day_rng_atr','vol60_vs_day','hour','d1_ret12','h4_ret12','m15_adx','d1_atr_ratio','h1_er10','m15_bar_atr']:
        ch=lab.online_best_policy(rows,cands,known,regime=F[reg].values[rows],nbins=3,prior=20)
        m,rr,R=lab.evaluate('F8',full(ch)); res[(name,reg)]=m
        print(name,reg,{k:m[k] for k in ['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','q_pos','eq_R2']})
# cost stress for fixed policies
print('cost stress (extra $/oz round-trip):')
for sq,tp in [('k50','f50'),('k70','f50'),('k90','f50'),('k90','f30'),('k50','1R')]:
    j=pid(sq,tp); rr,R,X=lab.run_slot('F8',j)
    for ex in [0,0.34,0.68]:
        R2=R-ex/(S[sq].values[rr]*S.atr.values[rr]); m=lab.metrics(R2,lab.TIME[rr])
        print(sq,tp,ex,{k:m[k] for k in ['n','PF','sumR','maxDD_R','ret_dd','months_pos','eq_R2']})
