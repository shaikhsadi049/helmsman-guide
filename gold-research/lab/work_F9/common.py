import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab"); import lab, numpy as np, pandas as pd
S=lab.SIG; F=lab.load_F(); R_=lab.load_R(); X_=lab.load_X(); N=len(S); B=3673
ALL=list(range(3600,3780))
f9=np.where(S.slot=='F9')[0]; fade=np.where(S.kind=='fade')[0]
def adaptive_exit(rows=f9, cands=ALL):
    kn=lab.known_bar(rows,cands); ch=lab.online_best_policy(rows,cands,kn); full=np.full(N,B); full[rows]=ch; return full
def show(nm,choice=None,take=None):
    m,rr,R=lab.evaluate('F9',choice,take)
    print(f"{nm:45s}",{k:m[k] for k in ('n','win','PF','sumR','avgR','maxDD_R','months_pos','q_pos','weeks_pos_pct','eq_R2','ulcer_R')},flush=True); return m,rr,R
def online_bin_rule(rows, x, y, known, nb=4, prior=10, minn=40):
    """skip a signal if its feature bin (edges = past quantiles) had a shrunk past mean R < 0"""
    m=lab.M1[rows]; ms=lab._ms(); take=np.ones(len(rows),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m>=a)&(m<b)
        if not te.any(): continue
        tr=known<a
        if tr.sum()<minn: continue
        e=np.nanquantile(x[tr],np.linspace(0,1,nb+1)[1:-1]); bt=np.searchsorted(e,x[tr]); bs=np.searchsorted(e,x[te])
        mu0=y[tr].mean()
        mus=np.array([(y[tr][bt==k].sum()+prior*mu0)/((bt==k).sum()+prior) for k in range(nb)])
        take[te]=mus[bs]>0
    return take
