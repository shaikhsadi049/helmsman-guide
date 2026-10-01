from common import *
F=F7(); ms=np.load("ms.npy")
def thr(f,qq,EX,sign=1):
    known=X7[:,EX]; x=F[f].values*sign; take=np.ones(len(rows),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        te=(M>=a)&(M<b); tr=known<a; take[te]=~(x[te]>np.nanquantile(x[tr],qq))
    return take
rows_=[]
for EX in (82,130,1282,BASE):
    m=met(EX); rows_.append(dict(exit=pname(EX),filt="none",**short(m)))
    for f in ("h1_adx","h4_rng20_atr","h4_di","h1_ribbon"):
        for qq in (0.7,0.8,0.9):
            m=met(EX,thr(f,qq,EX)); rows_.append(dict(exit=pname(EX),filt=f"{f}>q{int(qq*100)}",**short(m)))
    tk=thr("h1_adx",0.8,EX)&thr("h4_rng20_atr",0.8,EX); m=met(EX,tk); rows_.append(dict(exit=pname(EX),filt="adx&rng20 q80",**short(m)))
d=pd.DataFrame(rows_); pd.set_option("display.width",250); print(d.to_string()); d.to_pickle("neigh.pkl")
