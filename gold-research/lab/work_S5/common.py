import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab')
import lab, numpy as np, pandas as pd, os
W=os.path.dirname(os.path.abspath(__file__))
S=lab.SIG; SLOT='S5'
ROWS=np.where(S.slot.values==SLOT)[0]          # incl warm-up, time sorted
T=lab.TIME[ROWS]; IN=np.asarray(T>=lab.D0)
NP=3600
def cache():
    f=W+'/RX.npz'
    if os.path.exists(f): z=np.load(f); return z['R'],z['X']
    R=np.asarray(lab.load_R()[ROWS,:NP]); X=np.asarray(lab.load_X()[ROWS,:NP]); np.savez(f,R=R,X=X); return R,X
RS,XS=cache()
M1=S.m1.values[ROWS]
def run(pol, take=None):
    """pol: int or array len(ROWS) (column idx); take: bool len(ROWS). 2025+ only, greedy."""
    pol=np.full(len(ROWS),pol) if np.isscalar(pol) else np.asarray(pol)
    tk=IN.copy() if take is None else IN&np.asarray(take)
    idx=np.where(tk)[0]; r=RS[idx,pol[idx]]; x=XS[idx,pol[idx]]
    out=[]; free=-1
    for k,i in enumerate(idx):
        if free<M1[i]: out.append(k); free=x[k]
    out=np.array(out,int); return idx[out], r[out]
def met(pol,take=None):
    i,r=run(pol,take); return lab.metrics(r,T[i])
def qtr(t): return pd.DatetimeIndex(t).tz_localize(None).to_period('Q')
lab._MS=np.load(W+'/ms.npy')
F=None
def feats():
    global F
    if F is None: F=lab.load_F().iloc[ROWS].reset_index(drop=True)
    return F
def bestpol_local(cands, known, regime=None, nbins=3, prior=20):
    """same logic as lab.online_best_policy but on cached RS (cands are column idx)"""
    Rm=RS[:,cands]; ms=lab._MS; choice=np.full(len(ROWS),cands[0])
    for a,b in zip(ms[:-1],ms[1:]):
        test=(M1>=a)&(M1<b)
        if not test.any(): continue
        tr=known<a
        if tr.sum()<30: continue
        mu_all=np.nanmean(Rm[tr],0)
        if regime is None: choice[test]=cands[int(np.argmax(mu_all))]; continue
        edges=np.nanquantile(regime[tr],np.linspace(0,1,nbins+1)[1:-1])
        btr=np.searchsorted(edges,regime[tr]); bte=np.searchsorted(edges,regime[test]); best=[]
        for k in range(nbins):
            sel=btr==k; nk=sel.sum(); mu=(np.nansum(Rm[tr][sel],0)+prior*mu_all)/(nk+prior); best.append(cands[int(np.argmax(mu))])
        choice[np.where(test)[0]]=np.array(best)[bte]
    return choice
def known_of(cands): return XS[:,cands].max(1)
