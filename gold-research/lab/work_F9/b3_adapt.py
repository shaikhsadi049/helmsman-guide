import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab"); import lab, numpy as np, pandas as pd
S=lab.SIG; F=lab.load_F(); N=len(S); b=3673
def pi(**k): return lab.policy_index(kind='fade',**k)[0]
ALL=list(range(3600,3780))
SMALL=[b,pi(sq='k70',tp='f70',be='be1',rat='none',hm=2.0),pi(sq='k70',tp='1R',be='none',rat='none',hm=2.0),pi(sq='k90',tp='1R',be='none',rat='none',hm=2.0),
       pi(sq='k90',tp='f50',be='none',rat='none',hm=1.0),pi(sq='k70',tp='mean',be='be1',rat='none',hm=2.0),pi(sq='k70',tp='f70',be='none',rat='none',hm=1.0),pi(sq='k50',tp='f50',be='none',rat='none',hm=1.0)]
HM=[pi(sq=s,tp=t,be='none',rat='none',hm=h) for s in ['k70','k90'] for t in ['f50','f70','1R'] for h in [1.0,2.0]]
f9=np.where(S.slot=='F9')[0]; fade=np.where(S.kind=='fade')[0]
def show(nm,choice_full):
    m,rr,R=lab.evaluate('F9',choice_full); 
    print(f"{nm:40s}",{k:m[k] for k in ('n','win','PF','sumR','maxDD_R','months_pos','q_pos','eq_R2','ulcer_R')})
    return m
show('baseline',None)
res={}
for cn,C in [('ALL',ALL),('SMALL',SMALL),('HM12',HM)]:
    for pool,rows in [('F9',f9),('fade',fade)]:
        kn=lab.known_bar(rows,C)
        for reg in [None,'h1_atr_rank','h4_adx','h4_er10','h1_adx','day_rng_atr','h4_atr_rank']:
            if reg and cn=='ALL': continue
            r=None if reg is None else F[reg].values[rows]
            ch=lab.online_best_policy(rows,C,kn,regime=r,nbins=2 if pool=='F9' else 3)
            full=np.full(N,b); full[rows]=ch
            m=show(f'{cn} pool={pool} reg={reg}',full); res[(cn,pool,reg)]=m
            if reg is None:
                sel=full[f9][lab.TIME[f9]>=lab.D0]; print('   choices:',pd.Series([str({k:v for k,v in lab.P[j].items() if k!='kind'}) for j in sel]).value_counts().head(4).to_dict())
