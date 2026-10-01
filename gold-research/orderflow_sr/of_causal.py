"""Causal skip rules from order flow, per slot. For a (slot, feature): each month, using only past resolved signals
(incl. 2024 warm-up), find which tail (bottom or top 20% of the feature, edges from the past) had mean R below the rest
by a shrunk margin; skip that tail this month. Applied to EVERY feature so we can see how many pass by luck."""
import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import lab
src = open("../lab/portfolio.py").read().split('if __name__ == "__main__":')[0]; P = {}; exec(compile(src, "portfolio", "exec"), P)
OF = pd.read_parquet("of_features.parquet"); SIG = lab.SIG; R_ = lab.load_R(); X_ = lab.load_X(); MS = lab._ms(); M1 = SIG.m1.values
out = []
for slot, (legs, w) in P["REC"].items():
    rows = np.where(SIG.slot.values == slot)[0]
    R = np.mean([np.asarray(R_[rows, j]) for j in legs], axis=0); X = np.max([np.asarray(X_[rows, j]) for j in legs], axis=0)
    keep0 = P["skip_mask"](slot, rows)                      # the lab's own causal filter (S4, S7) stays on
    m = M1[rows]; base = lab.metrics(R[keep0 & (lab.TIME[rows] >= lab.D0)][lab.greedy(rows[keep0 & (lab.TIME[rows] >= lab.D0)], X[keep0 & (lab.TIME[rows] >= lab.D0)])],
                                     lab.TIME[rows[keep0 & (lab.TIME[rows] >= lab.D0)]][lab.greedy(rows[keep0 & (lab.TIME[rows] >= lab.D0)], X[keep0 & (lab.TIME[rows] >= lab.D0)])])
    for f in OF.columns:
        x = OF[f].values[rows]; keep = keep0.copy()
        for a, b in zip(MS[:-1], MS[1:]):
            t = (m >= a) & (m < b)
            if not t.any(): continue
            past = (X < a) & np.isfinite(x)
            if past.sum() < 60: continue
            lo, hi = np.nanquantile(x[past], [0.2, 0.8]); Rp = np.clip(R[past], -1.5, 3); xp = x[past]
            rest_lo = Rp[xp > lo].mean(); rest_hi = Rp[xp < hi].mean()
            gap_lo = (Rp[xp <= lo].mean() - rest_lo) * (xp <= lo).sum() / ((xp <= lo).sum() + 20)
            gap_hi = (Rp[xp >= hi].mean() - rest_hi) * (xp >= hi).sum() / ((xp >= hi).sum() + 20)
            if min(gap_lo, gap_hi) < -0.15:                              # one tail clearly worse in the past
                bad = (x <= lo) if gap_lo < gap_hi else (x >= hi)
                keep[t & bad] = False
        live = keep & (lab.TIME[rows] >= lab.D0); rr = rows[live]; tk = lab.greedy(rr, X[live]); mm = lab.metrics(R[live][tk], lab.TIME[rr[tk]])
        out.append(dict(slot=slot, feat=f, base_sumR=base["sumR"], base_DD=base["maxDD_R"], base_m=base["months_pos"], base_R2=base["eq_R2"],
                        sumR=mm["sumR"], DD=mm["maxDD_R"], months=mm["months_pos"], R2=mm["eq_R2"], n=mm["n"]))
D = pd.DataFrame(out); D["d_sumR"] = D.sumR - D.base_sumR; D["d_DD"] = D.DD - D.base_DD
D.to_parquet("of_causal.parquet"); pd.set_option("display.width", 220)
for slot, g in D.groupby("slot"):
    better = g[(g.d_sumR > 0) & (g.d_DD <= 0)]
    print(f"{slot}: base {g.base_sumR.iloc[0]:+.1f}R DD {g.base_DD.iloc[0]} | features improving BOTH sumR and DD: {len(better)}/{len(g)} | median d_sumR {g.d_sumR.median():+.1f}")
    print("   best:", better.sort_values("d_sumR", ascending=False).head(3)[["feat", "sumR", "DD", "months", "R2", "n"]].round(2).to_dict("records"))
