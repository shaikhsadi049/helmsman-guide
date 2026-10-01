from common import *
F=lab.load_F(); Fs=F.iloc[rows].reset_index(drop=True); EX=144
Mo=np.asarray(T.tz_localize(None).to_period("M").astype(str)); d=S.dir.values[rows]
i,r=greedy_local(EX); mon=pd.Series(r,index=Mo[i]).groupby(level=0).sum()
ib,rb=greedy_local(BASE); monb=pd.Series(rb,index=Mo[ib]).groupby(level=0).sum()
tab=pd.DataFrame({"sig":pd.Series(Mo[IN]).value_counts().sort_index(),"long%":pd.Series(d[IN]>0,index=Mo[IN]).groupby(level=0).mean().mul(100).round(0),
 "meanR_sig":pd.Series(R4[IN,EX],index=Mo[IN]).groupby(level=0).mean().round(2),"rec_R":mon.round(1),"base_R":monb.round(1)})
for f in ["d1_atr_rank","d1_er10","h4_er30","h4_adx","h4_rng20_atr","d1_ret6","h1_adx","prev_rng_atr"]:
    tab[f]=pd.Series(Fs[f].values[IN],index=Mo[IN]).groupby(level=0).mean().round(2)
pd.set_option("display.width",250); print(tab.to_string())
bad=mon.index[mon<=0.25]; print("bad months (rec)", list(bad))
isb=np.isin(Mo,bad)&IN; isg=(~np.isin(Mo,bad))&IN
z=[]
for c in Fs.columns:
    x=Fs[c].values; s=np.nanstd(x[IN])
    if s>0: z.append((c,(np.nanmean(x[isb])-np.nanmean(x[isg]))/s))
z=sorted(z,key=lambda t:-abs(t[1])); print([(c,round(v,2)) for c,v in z[:15]])
# losing trades vs winners under rec exit among taken
print("taken trades: loss vs win feature diff")
L_=i[r<0]; W_=i[r>0]; z=[]
for c in Fs.columns:
    x=Fs[c].values; s=np.nanstd(x[IN])
    if s>0: z.append((c,(np.nanmean(x[L_])-np.nanmean(x[W_]))/s))
z=sorted(z,key=lambda t:-abs(t[1])); print([(c,round(v,2)) for c,v in z[:12]])
# long vs short
for dd in (1,-1):
    s=IN&(d==dd); print("dir",dd,"n",s.sum(),"meanR rec",R4[s,EX].mean().round(3),"base",R4[s,BASE].mean().round(3))
# big-day dependence
day=pd.Series(r,index=T[i].tz_localize(None).floor("D")).groupby(level=0).sum(); print(day.nlargest(5).round(2))
