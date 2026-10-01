from common import *
import warnings; warnings.filterwarnings('ignore')
F=feats(); P=lab.P
def pid(**kw): return lab.policy_index(kind='trend',**kw)[0]
base=8
C1=[8,12,14,972,964,1012,2213, pid(sq='k50',tp='2R',part='slot',be='none',trail='h4q50',rat='q70k50',ts='none'),
    pid(sq='k50',tp='f50',part='slot',be='none',trail='h4q50',rat='none',ts='none'), pid(sq='k50',tp='1R',part='slot',be='none',trail='h4q50',rat='none',ts='none'),
    88, pid(sq='k50',tp='none',part='half@f30',be='none',trail='h4q50',rat='none',ts='none')]
C2=[8,12,972,1012]          # small set
C3=[8,972]
K=['n','win','PF','sumR','maxDD_R','ret_dd','months_pos','eq_R2','ulcer_R','top5days_pct']
def show(name,pol): m=met(pol); print(f'{name:40s}',{k:m[k] for k in K})
show('baseline',8); show('fixed 972',972)
for nm,C in [('C1',C1),('C2',C2),('C3',C3)]:
    kn=known_of(C)
    show(f'{nm} global mean',bestpol_local(C,kn))
    # throughput objective: R per held day -> transform via own loop
    for reg in ['h4_atr_rank','d1_atr_rank','h4_er30','h4_adx','d1_adx','day_rng_atr','hour','h4_ribbon','d1_ribbon','d1_dist200','h1_atr_rank','m5_atr_rank','d1_ret24','dxy_trend']:
        show(f'{nm} regime {reg}',bestpol_local(C,kn,F[reg].values.astype(float)))
    show(f'{nm} regime dir',bestpol_local(C,kn,S.dir.values[ROWS].astype(float),nbins=2))
