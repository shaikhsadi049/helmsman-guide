import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "../lab")
import xexit as XE, lab
SIG = lab.SIG; F = lab.load_F(); MS = lab._ms(); M1 = SIG.m1.values
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
FAST = {"S3", "S5", "S6", "S7"}
for slot in SQ:
    rows = np.where(SIG.slot.values == slot)[0]; s = SIG.iloc[rows]; tf = s.tf.iloc[0]
    k = np.clip(s[SQ[slot]].values, 0.5, 8.0); risk = k * s.atr.values; hor = np.full(len(rows), 14400)
    A = dict(tp=3 if slot in FAST else 5, be=(1.0, 0.05), trail=None); B = dict(tp=0, be=(1.0, 0.05), trail=("chand", "4h:atr:14", 1.5))
    RA, XA = XE.run(s.m1.values, s.dir.values, s.lvl.values, risk, hor, tp=A["tp"], be=A["be"], trail=A["trail"], tf_flag=tf)
    RB, XB = XE.run(s.m1.values, s.dir.values, s.lvl.values, risk, hor, tp=B["tp"], be=B["be"], trail=B["trail"], tf_flag=tf)
    RA, RB, XA, XB = map(np.asarray, (RA, RB, XA, XB)); m = M1[rows]; known = np.maximum(XA, XB); live = lab.TIME[rows] >= lab.D0
    def book(R, X):
        rr = rows[live]; tk = lab.greedy(rr, X[live]); return lab.metrics(R[live][tk], lab.TIME[rr[tk]])
    out = {"A fixed target": book(RA, XA), "B H4 trail": book(RB, XB)}
    for feat in ("h1_atr_rank", "h1_er30"):
        x = F[feat].values[rows]; use_b = np.zeros(len(rows), bool)
        for a, b in zip(MS[:-1], MS[1:]):
            t = (m >= a) & (m < b); past = known < a
            if not t.any() or past.sum() < 60: continue
            e = np.nanquantile(x[past], [1/3, 2/3]); cp = np.searchsorted(e, x[past]); ct = np.searchsorted(e, x[t])
            for c in range(3):
                pc = cp == c
                dA = np.clip(RA[past][pc], -1.5, 5).mean() if pc.any() else 0; dB = np.clip(RB[past][pc], -1.5, 5).mean() if pc.any() else 0
                use_b[np.where(t)[0][ct == c]] = dB > dA
        R = np.where(use_b, RB, RA); X = np.where(use_b, XB, XA); out[f"causal A/B by {feat}"] = book(R, X)
    print(f"== {slot}")
    for k_, v in out.items(): print(f"   {k_:28s} {v['sumR']:+6.1f}R DD {v['maxDD_R']:4.1f} m+ {v['months_pos']} R2 {v['eq_R2']} top5 {v['top5days_pct']}%")
    base = lab.evaluate(slot)[0]; print(f"   {'(Assay today, 1m sim)':28s} {base['sumR']:+6.1f}R DD {base['maxDD_R']:4.1f} m+ {base['months_pos']}")
