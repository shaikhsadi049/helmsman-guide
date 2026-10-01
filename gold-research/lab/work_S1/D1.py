from h import *
F = lab.load_F().iloc[rows].reset_index(drop=True)
i, r = run(BASE)
tk = np.zeros(len(rows),bool); tk[i]=True
idx = np.where(in25)[0]
print("taken mean", r.mean(), " non-taken 2025+ signals: n", (~tk[idx]).sum(), "mean R", R1[idx[~tk[idx]],BASE].mean().round(3), "sum", R1[idx[~tk[idx]],BASE].sum().round(1))
print("taken: per-signal R under 1320", R1[i,1320].mean(), " non-taken under 1320", R1[idx[~tk[idx]],1320].mean())
mon = T.tz_localize(None).to_period("M")
s = pd.Series(r, index=mon[i]).groupby(level=0).sum()
bad = s[s<=0.3].index; good = s[s>1].index
print("bad/flat months", list(map(str,bad))); print("good months", list(map(str,good)))
feat = ["d1_atr_rank","h4_atr_rank","h1_atr_rank","d1_adx","h4_adx","d1_er10","h4_er30","d1_ret24","d1_ret48","h4_z20","d1_slope50","h4_slope50","d1_ribbon","dist_prev_hi","day_rng_atr","h1_atr_ratio","d1_vr10","h4_vr10","dxy_trend","dxy_z20","hour"]
# all signals of the month (market state)
A = F.loc[idx, feat].copy(); A["mon"]=mon[idx]; A["R"]=R1[idx,BASE]; A["dir"]=S.dir.values[idx]
A["grp"] = np.where(A.mon.isin(bad),"bad",np.where(A.mon.isin(good),"good","mid"))
pd.set_option('display.width',250)
g = A.groupby("grp")[feat+["R"]].mean().T; g["diff_sd"]=(g["bad"]-g["good"])/A[feat+["R"]].std(); print(g.round(3).sort_values("diff_sd").to_string())
# per month summary
mm = A.groupby("mon").agg(nsig=("R","size"), sigR=("R","mean"), long=("dir",lambda x:(x>0).mean()), d1atr=("d1_atr_rank","mean"), d1er=("d1_er10","mean"), h4z=("h4_z20","mean"), d1ret24=("d1_ret24","mean"), vr=("d1_vr10","mean"))
mm["tradeR"]=s; print(mm.round(2).to_string())
# losing trades
L = pd.DataFrame({"t":T[i].tz_localize(None),"dir":S.dir.values[i],"R":r}); print(L[L.R<0].to_string())
