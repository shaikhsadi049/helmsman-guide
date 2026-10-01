from common import *
import itertools, warnings; warnings.filterwarnings('ignore')
P=lab.P
def gre(idx,pol):
    r=RS[idx,pol]; x=XS[idx,pol]; out=[]; free=-1
    for k,i in enumerate(idx):
        if free<M1[i]: out.append(k); free=x[k]
    return idx[np.array(out,int)], r[out]
def score(r,kind):
    if len(r)==0: return -9
    eq=np.cumsum(r); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
    if kind=='sum': return eq[-1]
    if kind=='retdd': return eq[-1]/(dd+2)
    if kind=='sharpe': return r.mean()/r.std()*np.sqrt(len(r))
fam=[j for j,p in enumerate(P[:NP]) if p['trail'] in ('h4q50',) and p['part'] in('slot','none')]
print(len(fam))
ms=lab._MS; allidx=np.arange(len(ROWS))
for kind in ['sum','retdd','sharpe']:
  for look in [None, 365]:
    choice=np.full(len(ROWS),8); picks=[]
    for a,b in zip(ms[:-1],ms[1:]):
        test=(M1>=a)&(M1<b)
        if not test.any(): continue
        sc=[]
        for j in fam:
            tr=np.where(XS[:,j]<a)[0]   # outcome known under this policy
            if look: tr=tr[(T[tr]>=T[test][0]-pd.Timedelta(days=look))]
            _,r=gre(tr,j); sc.append(score(r,kind))
        jb=fam[int(np.argmax(sc))]; choice[test]=jb; picks.append(jb)
    m=met(choice); print(kind,look,{k:m[k] for k in ['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','eq_R2','ulcer_R','top5days_pct']})
    print('   picks',[ (P[j]['sq'],P[j]['tp'],P[j]['part'],P[j]['be'],P[j]['rat'],P[j]['ts']) for j in picks][::3])
