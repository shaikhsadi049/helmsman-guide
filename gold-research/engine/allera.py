"""Pick configs that work in EVERY era: 2012-16, 2017-19, 2020-22 (XAUUSD) + Y1, Y2 (GC 2024-26).
Then blind-test the picks on GC 2023-03..2024-07 (never used for picking)."""
import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
dec = pd.read_parquet("decade_grid.parquet")
gc = pd.read_parquet("adv_results.parquet")
ES = pickle.load(open("adv_entry_sets.pkl", "rb"))
key = ["es","k","adapt","r1","f1","lock","ttf","trail","brk","gb_a","gb_g"]
m = dec.merge(gc, on=key)
m["tf"] = [ES[i][0] for i in m.es]
eras_pf = ["pf_A","pf_B","pf_C","pf1","pf2"]; eras_R = ["R_A","R_B","R_C","R1","R2"]
m["pf_min"] = m[eras_pf].min(axis=1); m["all_pos"] = (m[eras_R] > 0).all(axis=1)
m["win_min"] = m[["win_A","win_B","win_C","win1","win2"]].min(axis=1)
m["n_min"] = m[["n_A","n_B","n_C","n1","n2"]].min(axis=1)
print("merged configs:", len(m), "| profitable in ALL 5 eras:", m.all_pos.sum())
ok = m[m.all_pos & (m.n_min >= 25)]
print("…with >=25 trades in each era:", len(ok))
for tf, g in ok.groupby("tf"):
    print(f"  {tf}: {len(g)} | pf_min>=1.2: {(g.pf_min>=1.2).sum()} | pf_min>=1.3: {(g.pf_min>=1.3).sum()} | win_min>=55: {(g.win_min>=55).sum()}")
ok.to_parquet("allera_ok.parquet")
cols = ["tf","es","k","adapt","r1","f1","lock","ttf","trail","brk","gb_a","gb_g","pf_A","pf_B","pf_C","pf1","pf2","R_A","R_B","R_C","R1","R2","win_min","yrs_pos"]
print(ok.sort_values("pf_min", ascending=False)[cols].head(20).round(2).to_string(index=False))
