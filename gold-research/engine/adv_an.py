import pickle, numpy as np, pandas as pd
pd.set_option("display.width", 280); pd.set_option("display.max_columns", 40)
df = pd.read_parquet("adv_results.parquet"); ES = pickle.load(open("adv_entry_sets.pkl", "rb"))
df["tf"] = [ES[i][0] for i in df.es]; df["entry"] = [f"{ES[i][1]}{ES[i][2] if ES[i][1]=='pullback' else ''}" for i in df.es]
df["conf"] = ["+".join(ES[i][3]) or "-" for i in df.es]; df["adx"] = [ES[i][4] for i in df.es]; df["sess"] = [str(ES[i][5]) for i in df.es]
print("configs:", len(df), "| Y1 profitable:", round((df.R1 > 0).mean()*100,1), "% | Y2 profitable:", round((df.R2 > 0).mean()*100,1), "% | corr(R1,R2):", round(df.R1.corr(df.R2),3))
cols = ["tf","entry","conf","adx","sess","k","adapt","r1","f1","lock","ttf","trail","brk","gb_a","gb_g","n1","win1","pf1","R1","dd1","aw1","mx1","n2","win2","pf2","R2","dd2","aw2","mx2"]
def pick(d, name, cond, key, top=8):
    c = d[cond(d)].copy()
    c["key"] = key(c)
    c = c.sort_values("key", ascending=False)
    print(f"\n===== {name}: {len(c)} qualify on Y1. Top {top} by Y1 -> their UNSEEN Y2:")
    print(c[cols].head(top).round(2).to_string(index=False))
    h = c.head(50)
    print(f"   top-50 on Y1 -> Y2 median: win {h.win2.median():.0f}%  PF {h.pf2.median():.2f}  R {h.R2.median():+.1f}  DD {h.dd2.median():.1f} | share Y2 profitable {(h.R2>0).mean()*100:.0f}%")
    return c
for tf in ["5min", "15min", "1h"]:
    d = df[df.tf == tf]
    print(f"\n\n################ {tf}")
    pick(d, f"{tf} HIGH-WIN (win>=60%, PF>=1.3)", lambda x: (x.win1 >= 60) & (x.pf1 >= 1.3) & (x.n1 >= 40), lambda x: x.R1)
    pick(d, f"{tf} BALANCED (win>=50%) by R/DD", lambda x: (x.win1 >= 50) & (x.n1 >= 40) & (x.R1 > 0), lambda x: x.R1 / x.dd1.clip(lower=3))
    pick(d, f"{tf} BIG-RUNNER by R/DD", lambda x: (x.n1 >= 40) & (x.R1 > 0), lambda x: x.R1 / x.dd1.clip(lower=3))
# what drives Y2 across all configs (median R2 by setting)
for c in ["tf","entry","conf","adx","sess","k","adapt","r1","f1","lock","ttf","trail","brk","gb_a"]:
    g = df.groupby(c).agg(R2=("R2","median"), win2=("win2","median"), pf2=("pf2","median"), R1=("R1","median"))
    print("\n--", c, "\n", g.round(2).T.to_string())
