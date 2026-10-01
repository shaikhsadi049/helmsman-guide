from common import *
import pickle
d=pickle.load(open("shadow2.pkl","rb")); ch,log=d["res"]["small12|ret_ulcer|exp"]; TK=d["TK"]
fi=pickle.load(open("final.pkl","rb")); mon=fi["mon"]; port=fi["port"]
df=pd.DataFrame(dict(port=port,s7base=mon.base,s7rec=mon.rec)).fillna(0)
print(df.round(1).to_string())
print("port months<0:",(df.port<0).sum(),"; in those S7rec sum",df.s7rec[df.port<0].sum().round(1),"S7base",df.s7base[df.port<0].sum().round(1))
for w in (0.5,1.0):
    c=df.port+w*df.s7rec; eq=c.cumsum(); print(f"port+{w}*S7rec: sum {c.sum():.1f} months_pos {(c>0).sum()}/19 monthly-eq maxDD {(eq.cummax()-eq).max():.1f}")
c=df.port; eq=c.cumsum(); print(f"port alone: sum {c.sum():.1f} months_pos {(c>0).sum()}/19 monthly-eq maxDD {(eq.cummax()-eq).max():.1f}")
c=df.port+df.s7base; eq=c.cumsum(); print(f"port+S7base: sum {c.sum():.1f} months_pos {(c>0).sum()}/19 monthly-eq maxDD {(eq.cummax()-eq).max():.1f}")
# D1 efficiency gate test
F=F7(); ms=np.load("ms.npy")
for f in ("d1_er30","d1_er10","h4_adx","h4_er30"):
    x=F[f].values; 
    for qq in (0.2,0.3):
        take=np.ones(len(rows),bool)
        for a,b in zip(ms[:-1],ms[1:]):
            te=(M>=a)&(M<b); take[te]=~(x[te]<np.nanquantile(x[M<a],qq))
        print(f"gate skip {f}<q{int(qq*100)}", short(met(ch,TK&take)))
