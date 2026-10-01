import sys; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
S=lab.SIG; F=lab.load_F(); R_=lab.load_R()
def pid(sq,tp,hm=1.0): return lab.policy_index(kind='fade',sq=sq,tp=tp,be='none',rat='none',hm=hm)[0]
rows=np.where(S.slot=='F8')[0]; ms=lab._ms(); m1=lab.M1[rows]
K=['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','q_pos','eq_R2','ulcer_R']
def full(ch):
    a=np.full(len(S),lab.baseline_policy('F8')); a[rows]=ch; return a
def learner(C,crit,window=None,known=None):
    known=lab.known_bar(rows,C) if known is None else known
    Rm=np.stack([np.asarray(R_[rows,j]) for j in C],1); ch=np.full(len(rows),C[0])
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m1>=a)&(m1<b); tr=known<a
        if window: tr=tr&(m1>=a-window*30*1440)
        if not te.any() or tr.sum()<30: continue
        X=Rm[tr]
        if crit=='mean': sc=X.mean(0)
        elif crit=='dd':
            eq=np.cumsum(X,0); dd=(np.maximum.accumulate(eq,0)-eq).max(0); sc=X.sum(0)/np.maximum(dd,1)
        elif crit=='pf': sc=np.where(X>0,X,0).sum(0)/np.maximum(-np.where(X<0,X,0).sum(0),1e-9)
        ch[te]=C[int(np.argmax(sc))]
    return ch
sets={'C12':[pid(s,t) for s in ['k50','k70','k90'] for t in ['f30','f50','f70','1R']],
      'C6':[pid(s,t) for s in ['k50','k70'] for t in ['f30','f50','f70']],
      'C9':[pid(s,t) for s in ['k50','k70','k90'] for t in ['f30','f50','f70']],
      'C24':[pid(s,t,h) for s in ['k50','k70','k90'] for t in ['f30','f50','f70','1R'] for h in [1.0,2.0]],
      'C60all':[j for j,p in enumerate(lab.P) if p['kind']=='fade' and p['hm']==1.0]}
for sn,C in sets.items():
    kn=lab.known_bar(rows,C)
    for crit in ['mean','dd','pf']:
        for w in [None,12]:
            ch=learner(C,crit,w,kn); m,rr,R=lab.evaluate('F8',full(ch))
            print(sn,crit,w,{k:m[k] for k in K},flush=True)
