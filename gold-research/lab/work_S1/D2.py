from h import *
F = lab.load_F().iloc[rows].reset_index(drop=True)
def prank(f):
    x=F[f].values; out=np.full(len(x),np.nan)
    for k in range(len(x)):
        p = M < M[k]
        if p.sum()>=50: out[k]=(x[p]<x[k]).mean()
    return out
for f in ["d1_adx","d1_ret48","d1_atr_rank","dxy_z20"]:
    pr = prank(f)
    for EX in (1200,1248,1254,1320):
        line=[]
        for th in (0.7,0.8,0.9):
            tk = ~(pr>th) if f!="dxy_z20" else ~(pr<1-th)
            m=met(EX,tk); line.append(f"{th}: n{m['n']} {m['sumR']}R dd{m['maxDD_R']} {m['months_pos']} r2 {m['eq_R2']}")
        m0=met(EX); print(f, EX, f"base {m0['sumR']}R dd{m0['maxDD_R']} {m0['months_pos']} |", " | ".join(line))
