"""Causal monthly exit choice among the 274-exit menu per trend slot (score = past one-at-a-time book sumR/max(maxDD,1),
outcomes known before the month), vs the fixed lab recommendation and today's Assay exit."""
import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "../lab")
import xexit as XE, lab
SIG = lab.SIG; MS = lab._ms(); M1 = SIG.m1.values
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
def book(R, X, m, upto):
    ok = X < upto; R, X, m = R[ok], X[ok], m[ok]; take = np.zeros(len(R), bool); free = -1
    for k in range(len(R)):
        if m[k] > free: take[k] = True; free = X[k]
    r = R[take]
    if len(r) < 10: return -np.inf
    eq = np.cumsum(r); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max(); return eq[-1] / max(dd, 1.0)
out = {}
for slot in SQ:
    rows = np.where(SIG.slot.values == slot)[0]; s = SIG.iloc[rows]; tf = s.tf.iloc[0]
    k = np.clip(s[SQ[slot]].values, 0.5, 8.0); risk = k * s.atr.values; hor = np.full(len(rows), 14400)
    menu = XE.exit_menu(tf); RR = []; XX = []
    for ex in menu:
        R, X = XE.run(s.m1.values, s.dir.values, s.lvl.values, risk, hor, tp=ex["tp"], be=ex["be"], trail=ex["trail"], stall=ex.get("stall", 0),
                      prog=ex.get("prog", (0, 0.0)), gb=ex.get("gb", (0, 0.0)), tf_flag=tf)
        RR.append(np.asarray(R)); XX.append(np.asarray(X))
    RR = np.stack(RR); XX = np.stack(XX); m = M1[rows]
    choice = np.zeros(len(rows), int); picks = []
    for a, b in zip(MS[:-1], MS[1:]):
        t = (m >= a) & (m < b)
        if not t.any(): continue
        sc = [book(RR[j], XX[j], m, a) for j in range(len(menu))]; j = int(np.argmax(sc)); choice[t] = j; picks.append(j)
    R = RR[choice, np.arange(len(rows))]; X = XX[choice, np.arange(len(rows))]
    live = lab.TIME[rows] >= lab.D0; rr = rows[live]; tk = lab.greedy(rr, X[live]); mc = lab.metrics(R[live][tk], lab.TIME[rr[tk]])
    mb = lab.evaluate(slot)[0]
    out[slot] = (mb, mc)
    from collections import Counter
    top = Counter(picks).most_common(2)
    print(f"{slot}: today {mb['sumR']:+.1f}R DD {mb['maxDD_R']} m+ {mb['months_pos']} R2 {mb['eq_R2']} | CAUSAL 274-menu {mc['sumR']:+.1f}R DD {mc['maxDD_R']} m+ {mc['months_pos']} R2 {mc['eq_R2']} top5 {mc['top5days_pct']}%"
          f" | most chosen: " + " / ".join(f"{XE.describe(menu[j])} ({n}m)" for j, n in top), flush=True)
    np.save(f"xc_{slot}_R.npy", R); np.save(f"xc_{slot}_X.npy", X)
