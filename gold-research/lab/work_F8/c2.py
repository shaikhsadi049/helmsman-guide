import sys; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd
S=lab.SIG; R_=lab.load_R()
rows=np.where(S.slot=='F8')[0]; r25=rows[lab.TIME[rows]>=lab.D0]
def pid(sq,tp,hm=1.0): return lab.policy_index(kind='fade',sq=sq,tp=tp,be='none',rat='none',hm=hm)[0]
print('UNGREEDY all 463 signals:')
for tp in ['f30','f50','f70','1R']:
  for sq in ['k50','k70','k90']:
    m=lab.metrics(np.asarray(R_[r25,pid(sq,tp)]),lab.TIME[r25]); print(sq,tp,{k:m[k] for k in ['PF','sumR','maxDD_R','ret_dd','months_pos','q_pos','eq_R2']})
C=[pid(s,t) for s in ['k50','k70','k90'] for t in ['f30','f50','f70','1R']]
known=lab.known_bar(rows,C); Rm=np.stack([np.asarray(R_[rows,j]) for j in C],1)
ms=lab._ms(); m1=lab.M1[rows]
def full(ch):
    a=np.full(len(S),lab.baseline_policy('F8')); a[rows]=ch; return a
for crit in ['sharpe','median','dd']:
    ch=np.full(len(rows),C[4])
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m1>=a)&(m1<b); tr=known<a
        if not te.any() or tr.sum()<30: continue
        X=Rm[tr]
        if crit=='sharpe': sc=X.mean(0)/X.std(0)
        elif crit=='median': sc=np.median(X,0)
        else:
            eq=np.cumsum(X,0); dd=(np.maximum.accumulate(eq,0)-eq).max(0); sc=X.sum(0)/np.maximum(dd,1)
        ch[te]=C[int(np.argmax(sc))]
    m,rr,R=lab.evaluate('F8',full(ch))
    sel=pd.Series(ch[lab.TIME[rows]>=lab.D0]).map(lambda j: f"{lab.P[j]['sq']}/{lab.P[j]['tp']}").value_counts().to_dict()
    print(crit,{k:m[k] for k in ['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','q_pos','eq_R2','ulcer_R']},sel)
