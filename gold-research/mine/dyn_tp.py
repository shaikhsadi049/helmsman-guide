"""Dynamic target: TP in R = quantile of the favourable move (MFE/k) of PAST resolved signals, optionally only those in the same
market regime (tercile of H1 ADX / H1 ATR-rank / H1 ER, edges from the past). Compared with fixed 3R/5R. BE at 1R everywhere."""
import sys, numpy as np, pandas as pd, pickle, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "../lab")
import xexit as XE, lab
SIG = lab.SIG; F = lab.load_F(); M1 = SIG.m1.values
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
def dyn_tp(rows, k, q, regime=None):
    mfeR = SIG.mfe_a.values[rows] / k; xend = SIG.xend.values[rows]; m = M1[rows]; tp = np.full(len(rows), np.nan)
    for i in range(len(rows)):
        past = xend[:i] < m[i]
        if regime is not None and past.sum() >= 60:
            e = np.nanquantile(regime[:i][past], [1/3, 2/3]); c = np.searchsorted(e, regime[i])
            same = past & (np.searchsorted(e, regime[:i]) == c)
            if same.sum() >= 30: past = same
        if past.sum() >= 30: tp[i] = np.quantile(mfeR[:i][past], q)
    return np.clip(np.nan_to_num(tp, nan=3.0), 0.5, 8.0)
out = []
for slot in SQ:
    rows = np.where(SIG.slot.values == slot)[0]; s = SIG.iloc[rows]; tf = s.tf.iloc[0]
    k = np.clip(s[SQ[slot]].values, 0.5, 8.0); risk = k * s.atr.values; hor = np.full(len(rows), 14400); live = lab.TIME[rows] >= lab.D0
    def book(tp):
        R, X = XE.run(s.m1.values, s.dir.values, s.lvl.values, risk, hor, tp=tp, be=(1.0, 0.05), trail=None, tf_flag=tf)
        R, X = np.asarray(R), np.asarray(X); rr = rows[live]; tk = lab.greedy(rr, X[live]); return lab.metrics(R[live][tk], lab.TIME[rr[tk]])
    cands = {"fixed 3R": 3.0, "fixed 5R": 5.0}
    for q in (0.5, 0.7):
        cands[f"measured q{q}"] = dyn_tp(rows, k, q)
        for rn, col in (("ADX", "h1_adx"), ("vol", "h1_atr_rank"), ("ER", "h1_er30")):
            cands[f"measured q{q} by {rn}"] = dyn_tp(rows, k, q, F[col].values[rows])
    for name, tp in cands.items():
        mm = book(tp); out.append(dict(slot=slot, tp=name, **{c: mm[c] for c in ("sumR", "maxDD_R", "months_pos", "eq_R2", "top5days_pct", "n")},
                                        median_TP=float(np.median(tp)) if not np.isscalar(tp) else tp))
    print(slot, "ok", flush=True)
T = pd.DataFrame(out); T.to_parquet("dyn_tp.parquet"); pd.set_option("display.width", 220)
print(T.round(2).to_string(index=False))
