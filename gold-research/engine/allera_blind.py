import numpy as np, pandas as pd, pickle, warnings
warnings.filterwarnings("ignore")
import holdout as H   # sets trade_ok to the blind window 2023-03 .. 2024-07
ES = pickle.load(open("adv_entry_sets.pkl", "rb"))
ok = pd.read_parquet("allera_ok.parquet")
for i in sorted(set(ok.es)): pass
def desc(es): e = ES[es]; return f"{e[0]} {e[1]}{e[2] if e[1]=='pullback' else ''} conf={'+'.join(e[3]) or '-'} adx={e[4]} sess={e[5]}"
cats = {
 "ROB-RUNNER 15m (top pf_min)": ok[ok.tf == "15min"].sort_values("pf_min", ascending=False).head(20),
 "ROB-HIGHWIN (win_min>=50)":   ok[ok.win_min >= 50].sort_values("pf_min", ascending=False).head(20),
 "ROB-1H (top pf_min)":         ok[ok.tf == "1h"].sort_values("pf_min", ascending=False).head(20),
 "ALL 6577 all-era configs":    ok,
}
for name, c in cats.items():
    c = c.copy(); c.index = range(len(c))
    rows = H.job(c)
    h = pd.DataFrame(rows, columns=["i", "n_h", "win_h", "pf_h", "R_h", "dd_h"]).set_index("i")
    c = c.join(h)
    print(f"\n### {name}: {len(c)} configs -> BLIND 2023-03..2024-07")
    print(f"   profitable {(c.R_h>0).mean()*100:.0f}% | median PF {c.pf_h.median():.2f} | median win {c.win_h.median():.0f}% | median R {c.R_h.median():+.1f} | median DD {c.dd_h.median():.1f}")
    if len(c) <= 20:
        for _, r in c.head(5).iterrows():
            print(f"   {desc(int(r.es)):55s} SL {r.k}{'a' if r.adapt else ''} TP1 {r.r1}x{r.f1} run {r.ttf} tr{r.trail} brk{int(r.brk)} gb{r.gb_a} | eras PFmin {r.pf_min:.2f} winmin {r.win_min:.0f}% || BLIND n={r.n_h:.0f} win={r.win_h:.0f}% PF={r.pf_h:.2f} R={r.R_h:+.1f}")
    c.to_parquet("allera_blind_" + "".join(ch for ch in name if ch.isalnum())[:20] + ".parquet")
