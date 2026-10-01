from common import *
F=getF()
sets={"C_all6":[1208,2168,1928,3128,2288,2369],"C_base_3R":[1208,2168],"C_tp_k70slot":[1208,2168,1928,1688],
      "C_3Rfam":[2168,2288,2369,3128]}
regs=[None,"h4_atr_rank","d1_atr_rank","h4_er30","h4_adx","d1_adx","h1_er30","day_rng_atr","hour","d1_ret24","m15_atr_rank","h4_bbw_rank","d1_er30","h4_ret24"]
out=[]
for sn,c in sets.items():
    kn=known(c)
    for obj in ["mean","rate"]:
        for rg in regs:
            ch=online_choose(c, None if rg is None else F[rg].values, obj=obj, kn=kn)
            i,r=run(ch); m=short(met(i,r))
            vc=pd.Series(ch[IN25]).value_counts().to_dict()
            out.append(dict(set=sn,obj=obj,reg=rg,**m,choices=vc))
df=pd.DataFrame(out); pd.set_option('display.width',300); pd.set_option('display.max_colwidth',80)
print(df.to_string()); df.to_pickle("adaptive.pkl")
