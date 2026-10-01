from common import *
F=lab.load_F(); Fs=F.iloc[rows].reset_index(drop=True); EX=144; d=S.dir.values[rows]
for f in ["h4_stack","h1_stack","m15_stack","d1_stack"]:
    x=Fs[f].values
    print(f, pd.DataFrame({"x":x[IN],"y":R4[IN,EX],"q":Q[IN]}).pivot_table(index="x",columns="q",values="y",aggfunc="mean").round(2).to_string())
    print("   n", pd.Series(x[IN]).value_counts().to_dict())
for nm,take in [("h4_stack>=0",Fs.h4_stack.values>=0),("h4_stack==1",Fs.h4_stack.values==1),("h1_stack<1",Fs.h1_stack.values<1),("long only",d>0)]:
    print(nm, "skip%",round(100*(1-take[IN].mean())), short(M(EX,take)))
i,r=greedy_local(EX); print("greedy by dir", pd.Series(r).groupby(d[i]).agg(['count','sum','mean']).round(2))
