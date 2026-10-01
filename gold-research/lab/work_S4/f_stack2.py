from common import *
import json; C=json.load(open("cands.json"))
F=lab.load_F(); Fs=F.iloc[rows].reset_index(drop=True); ms=lab._ms()
h4=Fs.h4_stack.values
print("pre-2025 h4_stack==0 n", ((~IN)&(h4==0)).sum())
for k,EX in C.items():
    y=R4[:,EX]; kn=X4[:,EX]
    # causal: skip h4_stack!=1 when past resolved such signals (>=5) have mean<0
    take=np.ones(len(rows),bool); dec=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te=(m1>=a)&(m1<b); past=(kn<a)&(h4!=1)
        on=past.sum()>=5 and y[past].mean()<0; dec.append(int(on))
        if on: take[te&(h4!=1)]=False
    m0=M(EX); m1_=M(EX,take)
    print(f"{k:18s} sig-mean h4=0 {y[IN&(h4!=1)].mean():+.2f} vs h4=1 {y[IN&(h4==1)].mean():+.2f} | base {m0['sumR']} DD{m0['maxDD_R']} R2 {m0['eq_R2']} -> causal {m1_['sumR']} DD{m1_['maxDD_R']} R2 {m1_['eq_R2']} mpos {m1_['months_pos']} rule-on months {sum(dec)}/{len(dec)}")
