import sys; L="/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/"; sys.path.insert(0,L)
import lab, numpy as np, pandas as pd
S=lab.SIG; T=lab.TIME
ROWS=np.load(L+"work_F10/rows.npy"); RF=np.load(L+"work_F10/Rf.npy"); XF=np.load(L+"work_F10/Xf.npy")
POS={r:i for i,r in enumerate(ROWS)}
FP=lab.P[3600:3780]
def slot_rows(s, since=lab.D0, warm=False):
    r=np.where(S.slot.values==s)[0]
    return r if warm else r[T[r]>=since]
def sim(rows, pol, take=None):
    """pol: per-row local fade policy index (0..179) or int. returns taken rows, R"""
    li=np.array([POS[r] for r in rows]); pol=np.full(len(rows),pol) if np.isscalar(pol) else np.asarray(pol)
    tm=np.ones(len(rows),bool) if take is None else np.asarray(take)
    rr=rows[tm]; Rv=RF[li[tm],pol[tm]]; Xv=XF[li[tm],pol[tm]]
    tk=lab.greedy(rr,Xv); return rr[tk],Rv[tk]
def met(rr,R): return lab.metrics(R,T[rr])
def short(m,keys=("n","win","PF","sumR","maxDD_R","months_pos","q_pos","eq_R2","ulcer_R","top5days_pct")): return {k:(float(m[k]) if isinstance(m[k],(np.floating,float)) else m[k]) for k in keys}
def pname(j): p=FP[j]; return f"{p['sq']}/{p['tp']}/{p['be']}/{p['rat']}/h{p['hm']}"
BASE=lab.baseline_policy("F10")-3600
MS=np.load(L+"work_F10/ms.npy"); lab._MS=MS
M1=S.m1.values
F=lab.load_F()
def li_(rows): return np.array([POS[r] for r in rows])
def known(rows,cands): return XF[li_(rows)][:,cands].max(1)
def obp(rows, cands, regime=None, nbins=3, prior=20, mintr=30):
    """local re-implementation of lab.online_best_policy on cached fade R (local idx)"""
    Rm=RF[li_(rows)][:,cands]; kn=known(rows,cands); m=M1[rows]; ch=np.full(len(rows),cands[0])
    for a,b in zip(MS[:-1],MS[1:]):
        te=(m>=a)&(m<b)
        if not te.any(): continue
        tr=kn<a
        if tr.sum()<mintr: continue
        mu_all=np.nanmean(Rm[tr],0)
        if regime is None: ch[te]=cands[int(np.argmax(mu_all))]; continue
        e=np.nanquantile(regime[tr],np.linspace(0,1,nbins+1)[1:-1]); bt=np.searchsorted(e,regime[tr]); bb=np.searchsorted(e,regime[te])
        best=[]
        for k in range(nbins):
            sel=bt==k; mu=(np.nansum(Rm[tr][sel],0)+prior*mu_all)/(sel.sum()+prior); best.append(cands[int(np.argmax(mu))])
        ch[np.where(te)[0]]=np.array(best)[bb]
    return ch
def lj(**kw): return [j for j,p in enumerate(FP) if all(p.get(a)==b for a,b in kw.items())]
