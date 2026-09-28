import numpy as np, pandas as pd, pickle
K = pd.read_parquet("wfo_keys.parquet"); Z = np.load("wfo_monthly.npz"); R, N, W = Z["R"].astype(float), Z["N"].astype(float), Z["W"].astype(float)
ES = pickle.load(open("adv_entry_sets.pkl", "rb")); K["tf"] = [ES[i][0] for i in K.es]
# months index 0 = 2024-08 ; 2025-01 = 5 ; 2025-12 = 16 ; 2026-01..07 = 17..23
IS, OOS = slice(5, 17), slice(17, 24)
def agg(sl):
    r = R[:, sl]; n = N[:, sl].sum(1); w = W[:, sl].sum(1)
    eq = np.cumsum(r, 1); dd = (np.maximum.accumulate(np.concatenate([np.zeros((len(r), 1)), eq], 1), 1)[:, 1:] - eq).max(1)
    return r.sum(1), n, w / np.maximum(n, 1) * 100, dd, (r > 0).mean(1) * 100
K["R25"], K["n25"], K["win25"], K["dd25"], K["mp25"] = agg(IS)
K["R26"], K["n26"], K["win26"], K["dd26"], K["mp26"] = agg(OOS)
K["score"] = K.R25 / K.dd25.clip(lower=3)
def desc(r):
    e = ES[int(r.es)]
    return f"{e[0]:5s} {e[1]}{e[2] if e[1]=='pullback' else ''} conf={'+'.join(e[3]) or '-'} adx={e[4]} sess={e[5]} | SL {r.k}{'a' if r.adapt else ''} TP1 {r.r1}x{r.f1} lock {r.lock} run {r.ttf} tr{r.trail} brk{int(r.brk)} gb{r.gb_a}"
print(f"all configs: 2025 profitable {(K.R25>0).mean()*100:.0f}% | 2026 profitable {(K.R26>0).mean()*100:.0f}% (random baseline)")
for name, cond in [("ANY win-rate", K.n25 >= 30), ("win >= 50% in 2025", (K.n25 >= 30) & (K.win25 >= 50)), ("win >= 60% in 2025", (K.n25 >= 30) & (K.win25 >= 60))]:
    for tf in ["5min", "15min", "1h"]:
        c = K[cond & (K.tf == tf)].sort_values("score", ascending=False)
        top = c.head(50)
        print(f"\n== {name} | {tf}: top-50 by 2025 R/DD -> 2026 unseen: profitable {(top.R26>0).mean()*100:.0f}% | median 2026 R {top.R26.median():+.1f} | median win26 {top.win26.median():.0f}% | median DD26 {top.dd26.median():.1f}")
        for _, r in c.head(3).iterrows():
            print(f"   {desc(r)}\n      2025: n={r.n25:.0f} win={r.win25:.0f}% R={r.R25:+.1f} DD={r.dd25:.1f} months+={r.mp25:.0f}%  ||  2026: n={r.n26:.0f} win={r.win26:.0f}% R={r.R26:+.1f} DD={r.dd26:.1f} months+={r.mp26:.0f}%")
K.to_parquet("y2025_scores.parquet")
