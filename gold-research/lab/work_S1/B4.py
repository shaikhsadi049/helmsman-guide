from h import *
F = lab.load_F().iloc[rows].reset_index(drop=True)
sets = {"lock_vs_nolock":[1248,1320], "lock3":[1200,1248,1320], "wide":[1248,1320,1280,2004,1238,3204,1200],
        "smooth":[1248,1238,2004,3204,2284], "all_k70":[j for j in TREND if P[j]['sq']=='k70'], "allT":list(TREND)}
regs = [None,"h4_atr_rank","d1_atr_rank","h1_atr_rank","h4_adx","d1_adx","h4_er30","d1_er10","d1_ret48","d1_ribbon","dist_prev_hi","h1_atr_ratio","day_rng_atr","hour","d1_slope50"]
res=[]
for nm,c in sets.items():
    kn = lab.known_bar(rows, c)
    for rg in regs:
        if rg is not None and len(c)>50: continue
        for nb in ([3] if rg is None else [2,3]):
            ch = lab.online_best_policy(rows, c, kn, None if rg is None else F[rg].values, nbins=nb)
            m = met(ch); sw = pd.Series(ch[in25]).value_counts().head(3).to_dict()
            res.append(dict(set=nm, reg=rg, nb=nb, **{k:m[k] for k in ("n","PF","sumR","maxDD_R","ret_dd","months_pos","eq_R2","ulcer_R","top5days_pct")}, used=str(sw)))
            if rg is None: break
D=pd.DataFrame(res); pd.set_option('display.width',250); print(D.to_string())
D.to_csv("B4.csv")
