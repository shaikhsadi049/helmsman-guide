import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab"); import lab, numpy as np, pandas as pd, os
S=lab.SIG; ROWS=np.where(S.slot.values=="S3")[0]   # incl warm-up
IN25=np.asarray(lab.TIME[ROWS]>=lab.D0)
C="/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_S3/cache.npz"
if not os.path.exists(C):
    np.savez(C, R=np.asarray(lab.load_R()[ROWS]), X=np.asarray(lab.load_X()[ROWS]))
_c=np.load(C); RR=_c["R"]; XX=_c["X"]   # [n_S3, 3780]
M1=S.m1.values[ROWS]; T=lab.TIME[ROWS]
BASE=lab.baseline_policy("S3"); P=lab.P; TREND=np.arange(3600)
def greedy(idx, xb):
    take=np.zeros(len(idx),bool); free=-1; mm=M1[idx]
    for k in range(len(idx)):
        if free<mm[k]: take[k]=True; free=xb[k]
    return take
def run(pol, take=None):
    """pol: int or array over ROWS; take: bool over ROWS. returns local idx taken, R"""
    pol=np.full(len(ROWS),pol) if np.isscalar(pol) else np.asarray(pol)
    m=IN25.copy()
    if take is not None: m&=take
    idx=np.where(m)[0]; r=RR[idx,pol[idx]]; x=XX[idx,pol[idx]]
    tk=greedy(idx,x); return idx[tk], r[tk]
def met(idx,r): return lab.metrics(r, T[idx])
def short(m): return {k:m[k] for k in ("n","win","PF","sumR","maxDD_R","months_pos","q_pos","weeks_pos_pct","eq_R2","ulcer_R","top5days_pct")}
lab._MS=np.load("/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/work_S3/ms.npy")
MS=lab._MS
F=None
def getF():
    global F
    if F is None: F=lab.load_F().iloc[ROWS].reset_index(drop=True)
    return F
def known(cands): return XX[:,cands].max(axis=1)
def online_choose(cands, regime=None, nbins=3, prior=20, obj="mean", kn=None):
    """causal: per month choose candidate with best shrunk past objective (optionally per regime bucket)"""
    kn=known(cands) if kn is None else kn
    Rm=RR[:,cands]; H=(XX[:,cands]-M1[:,None]).astype(float)
    choice=np.full(len(ROWS),cands[0])
    for a,b in zip(MS[:-1],MS[1:]):
        te=(M1>=a)&(M1<b)
        if not te.any(): continue
        tr=kn<a
        if tr.sum()<30: continue
        def score(sel):
            if obj=="mean": return Rm[tr][sel].mean(0)
            if obj=="rate": return Rm[tr][sel].sum(0)/H[tr][sel].sum(0)   # R per minute in market
        sa=score(np.ones(tr.sum(),bool))
        if regime is None: choice[te]=cands[int(np.argmax(sa))]; continue
        edges=np.nanquantile(regime[tr],np.linspace(0,1,nbins+1)[1:-1])
        btr=np.searchsorted(edges,regime[tr]); bte=np.searchsorted(edges,regime[te])
        best=[]
        for k in range(nbins):
            sel=btr==k; nk=sel.sum()
            s=(score(sel)*nk+prior*sa)/(nk+prior) if nk>0 else sa
            best.append(cands[int(np.argmax(s))])
        choice[np.where(te)[0]]=np.array(best)[bte]
    return choice
def monthly(idx,r): return pd.Series(r,index=T[idx].tz_localize(None).to_period("M")).groupby(level=0).sum()
