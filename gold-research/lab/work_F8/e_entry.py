import sys; sys.path.insert(0,'..'); import lab, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
S=lab.SIG; F=lab.load_F(); R_=lab.load_R()
rows=np.where(S.slot=='F8')[0]
def pid(sq,tp,hm=1.0): return lab.policy_index(kind='fade',sq=sq,tp=tp,be='none',rat='none',hm=hm)[0]
ms=lab._ms(); m1=lab.M1[rows]
K=['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','q_pos','eq_R2','ulcer_R']
def ev(j,take):
    tm=np.zeros(len(S),bool); tm[rows]=take
    rr,R,X=lab.run_slot('F8',j,tm); m=lab.metrics(R,lab.TIME[rr]); return {k:m[k] for k in K}
for ename,j in [('base',lab.baseline_policy('F8')),('k50f50',pid('k50','f50'))]:
    y=np.asarray(R_[rows,j]); known=np.asarray(lab.load_X()[rows,j])
    print('==',ename,'no filter',ev(j,np.ones(len(rows),bool)))
    # online quintile rule: per feature, monthly: compute past quintile edges & mean R per quintile; skip extreme quintile (Q1 or Q5) if its shrunk past mean < 0
    for f in ['h4_er10','h1_adx','h1_er30','h1_er10','d1_ret12','prev_rng_atr','d1_adx','vol60_vs_day','m15_bar_atr','d1_er10','h4_atr_ratio','day_rng_atr','m15_rsi2','dir']:
        x=S.dir.values[rows].astype(float) if f=='dir' else F[f].values[rows]
        take=np.ones(len(rows),bool)
        for a,b in zip(ms[:-1],ms[1:]):
            te=(m1>=a)&(m1<b); tr=known<a
            if not te.any() or tr.sum()<60: continue
            if f=='dir':
                for d in (-1,1):
                    s=tr&(x==d); mu=y[s].sum()/(s.sum()+20)
                    if mu<0: take[te&(x==d)]=False
                continue
            e=np.nanquantile(x[tr],[0.2,0.8])
            lo=tr&(x<=e[0]); hi=tr&(x>=e[1])
            if y[lo].sum()/(lo.sum()+10)<0: take[te&(x<=e[0])]=False
            if y[hi].sum()/(hi.sum()+10)<0: take[te&(x>=e[1])]=False
        print(ename,'rule',f,'skip%',round(100*(1-take[lab.TIME[rows]>=lab.D0].mean())),ev(j,take))
