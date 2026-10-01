import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab"); import lab, numpy as np, pandas as pd
S=lab.SIG; R_=lab.load_R(); b=3673
def pi(**k): return lab.policy_index(kind='fade',**k)[0]
# paired per-signal diffs vs baseline by quarter for F9 and siblings
cands={'k70 f70 be1 hm2':pi(sq='k70',tp='f70',be='be1',rat='none',hm=2.0),'k70 f50 hm2':pi(sq='k70',tp='f50',be='none',rat='none',hm=2.0),
 'k70 f50 be1 hm2':pi(sq='k70',tp='f50',be='be1',rat='none',hm=2.0),'k70 1R hm2':pi(sq='k70',tp='1R',be='none',rat='none',hm=2.0),
 'k90 1R hm2':pi(sq='k90',tp='1R',be='none',rat='none',hm=2.0),'k90 f50 hm1':pi(sq='k90',tp='f50',be='none',rat='none',hm=1.0),
 'k70 f50 be1 hm1':pi(sq='k70',tp='f50',be='be1',rat='none',hm=1.0),'k70 f70 hm1':pi(sq='k70',tp='f70',be='none',rat='none',hm=1.0),
 'k70 f50 hm0.5':pi(sq='k70',tp='f50',be='none',rat='none',hm=0.5),'k50 f50 hm1':pi(sq='k50',tp='f50',be='none',rat='none',hm=1.0)}
for slot in ['F9','F8','F10','F11']:
    rows=np.where((S.slot==slot)&(lab.TIME>=lab.D0))[0]; q=lab.TIME[rows].tz_localize(None).to_period('Q')
    base=np.asarray(R_[rows,b]); print(f'\n{slot} n={len(rows)} base mean {base.mean():.3f}')
    for nm,j in cands.items():
        d=np.asarray(R_[rows,j])-base; qs=pd.Series(d).groupby(q.values).mean()
        print(f'  {nm:18s} dmean {d.mean():+.3f} t={d.mean()/d.std()*np.sqrt(len(d)):+.2f} qpos {(qs>0).sum()}/{len(qs)}  ' + ' '.join(f'{x:+.2f}' for x in qs))
