from common import *
import warnings; warnings.filterwarnings('ignore')
WU=~IN
def gw(j):
    idx=np.where(WU)[0]; r=RS[idx,j]; x=XS[idx,j]; out=[]; free=-1
    for k,i in enumerate(idx):
        if free<M1[i]: out.append(k); free=x[k]
    return idx[out], r[out]
rows=[]
for j in range(NP):
    i,r=gw(j); m=lab.metrics(r,T[i]); rows.append(dict(j=j,**{k:m[k] for k in ['n','sumR','maxDD_R','ret_dd','eq_R2','months_pos','top5days_pct']}))
D=pd.DataFrame(rows); D['rk_retdd']=D.ret_dd.rank(ascending=False); D['rk_sum']=D.sumR.rank(ascending=False)
print('warm-up signals',WU.sum(), T[WU].min(), T[WU].max())
print(D.loc[[8,12,14,972,964,1012,2213,88]].to_string())
P=lab.P
top=D.sort_values('ret_dd',ascending=False).head(10)
for j in top.j: print(j,P[j], top.loc[j,['sumR','maxDD_R','ret_dd']].tolist())
E=pd.read_pickle(W+'/exits_all.pkl')
# would the warm-up top-ret_dd policy have worked in 2025+?
for j in top.j[:5]: print('2025+ of warm-up top',j,E.loc[j,['n','sumR','maxDD_R','ret_dd','months_pos','eq_R2','top5days_pct']].tolist())
print('corr of warm-up ret_dd with 2025 ret_dd over policies', np.corrcoef(D.ret_dd, E.ret_dd)[0,1], ' sumR:',np.corrcoef(D.sumR,E.sumR)[0,1])
