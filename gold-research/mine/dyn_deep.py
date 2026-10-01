"""Sharper versions of findings 37-42 and how to USE them dynamically.
Base exit per slot from finding 42: fast slots (S3,S6,S7) A = TP 3R + BE1; slow slots (S1,S2,S4,S5) B = H4 chandelier 1.5 + BE1 (S1 uses A)."""
import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "../lab")
import xexit as XE, lab
from scipy.stats import spearmanr
SIG = lab.SIG; F = lab.load_F(); MS = lab._ms(); M1 = SIG.m1.values
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
EXA = {"S1", "S3", "S6", "S7"}
def past_rank(x, known, m):
    """causal percentile of each signal's feature among PAST signals of the same slot (outcome-independent, so all past signals count)"""
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        p = x[:i]; p = p[np.isfinite(p)]
        if len(p) >= 50 and np.isfinite(x[i]): out[i] = (p < x[i]).mean()
    return out
res = {}; table = []
for slot in SQ:
    rows = np.where(SIG.slot.values == slot)[0]; s = SIG.iloc[rows]; tf = s.tf.iloc[0]
    k = np.clip(s[SQ[slot]].values, 0.5, 8.0); risk = k * s.atr.values; hor = np.full(len(rows), 14400)
    if slot in EXA: R, X = XE.run(s.m1.values, s.dir.values, s.lvl.values, risk, hor, tp=3, be=(1.0, 0.05), trail=None, tf_flag=tf)
    else: R, X = XE.run(s.m1.values, s.dir.values, s.lvl.values, risk, hor, tp=0, be=(1.0, 0.05), trail=("chand", "4h:atr:14", 1.5), tf_flag=tf)
    R, X = np.asarray(R), np.asarray(X); m = M1[rows]
    feats = {"ADX(H1)": F.h1_adx.values[rows], "volatility ATR-rank(H1)": F.h1_atr_rank.values[rows], "efficiency ER30(H1)": F.h1_er30.values[rows],
             "ADX(H4)": F.h4_adx.values[rows], "volatility ATR-rank(H4)": F.h4_atr_rank.values[rows], "D1 ribbon with trade": F.d1_ribbon.values[rows]}
    pr = {f: past_rank(v, None, m) for f, v in feats.items()}
    res[slot] = dict(rows=rows, R=R, X=X, m=m, k=k, pr=pr, tf=tf, risk=risk, s=s)
    live = lab.TIME[rows] >= lab.D0; q = pd.PeriodIndex(lab.TIME[rows].tz_localize(None), freq="Q").astype(str)
    Rc = np.clip(R, -1.5, 5)
    for f, p in pr.items():
        ok = live & np.isfinite(p)
        dec = np.minimum((p[ok] * 5).astype(int), 4)                      # quintiles of the CAUSAL rank
        mq = pd.Series(Rc[ok]).groupby(dec).mean()
        ic = spearmanr(p[ok], Rc[ok]).correlation
        qs = [spearmanr(p[ok & (q == qq)], Rc[ok & (q == qq)]).correlation for qq in np.unique(q[ok])]
        icL = spearmanr(p[ok & (s.dir.values == 1)], Rc[ok & (s.dir.values == 1)]).correlation; icS = spearmanr(p[ok & (s.dir.values == -1)], Rc[ok & (s.dir.values == -1)]).correlation
        table.append(dict(slot=slot, feature=f, IC=ic, q_same=np.mean(np.sign(qs) == np.sign(ic)), IC_long=icL, IC_short=icS, **{f"Q{i+1}": mq.get(i, np.nan) for i in range(5)}))
    print(slot, "ok", flush=True)
T = pd.DataFrame(table); T.to_parquet("dyn_deep_curves.parquet")
pd.set_option("display.width", 250)
print(T.round(2).to_string(index=False))
import pickle; pickle.dump({k: {kk: vv for kk, vv in v.items() if kk != "s"} for k, v in res.items()}, open("dyn_deep_res.pkl", "wb"))
