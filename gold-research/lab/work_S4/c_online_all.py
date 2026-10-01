from common import *
ms=lab._ms(); known=X4.max(1)
def online_sel(crit, cset=np.arange(3600), lookback=None):
    ch=np.full(len(rows),BASE); log=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m1>=a)&(m1<b)
        if not te.any(): continue
        tr=known<a
        if lookback: tr&=(m1>=a-lookback)
        A=R4[tr][:,cset]
        mu=A.mean(0); sd=A.std(0)+1e-9
        if crit=="mean": s=mu
        elif crit=="sharpe": s=mu/sd
        elif crit=="sortino": s=mu/np.sqrt((np.minimum(A,0)**2).mean(0)+1e-9)
        elif crit=="median": s=np.median(A,0)
        j=cset[int(np.argmax(s))]; ch[te]=j; log.append((str(pd.Timestamp(lab.MONTHS[np.searchsorted(ms,a)]).date())[:7],pstr(j),tr.sum()))
    return ch,log
res=[]
for crit in ["mean","sharpe","sortino","median"]:
    for lb in [None, 6*30*1440]:  # all history / ~6 months of 1m bars (approx, m1 index counts trading minutes)
        ch,log=online_sel(crit,lookback=lb); m=M(ch); res.append(dict(crit=crit,lb=lb,**short(m)))
        if lb is None: print(crit, [l[1] for l in log][::3])
# restricted to non-slot part families
ok=np.array([j for j in range(3600) if P[j]["part"]!="slot"])
for crit in ["sharpe","sortino"]:
    ch,log=online_sel(crit,cset=ok); m=M(ch); res.append(dict(crit=crit+"_noslot",lb=None,**short(m)))
print(pd.DataFrame(res).to_string())
