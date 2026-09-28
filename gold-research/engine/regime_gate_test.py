import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import decade as D, regime_gate as RG
from contextlib import redirect_stdout
import io
rn = D.rn.copy(); h1 = D.h1.copy()
GF = RG.gate_features(D.base)
rn = rn.join(GF, on="t")
IS = rn.t.dt.year <= 2016
def s(R):
    if len(R) < 5: return "n<5"
    w = R > 0; eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    return f"n={len(R):4d} PF={R[w].sum()/-R[~w].sum():.2f} R={R.sum():+6.0f} DD={dd:4.0f}"
print("RN15 no gate      2012-16:", s(rn.R[IS].values), "| 2017-22:", s(rn.R[~IS].values))
rows = []
for col in ["er20", "er60", "er120", "adxD", "sep", "dist200"]:
    for q in (0.2, 0.3, 0.4, 0.5, 0.6):
        thr = rn[col][IS].quantile(q)
        m = rn[col] > thr
        a = rn.R[IS & m].values; b = rn.R[~IS & m].values
        rows.append((col, q, thr, a.sum(), a, b))
for n in (5, 10, 20):
    m = RG.equity_filter(rn.R.values, n)
    rows.append((f"equity{n}", 0, 0, rn.R[IS & m].sum(), rn.R[IS & m].values, rn.R[~IS & m].values))
rows.sort(key=lambda x: -x[3])
print("\nGates ranked by 2012-16 result (then shown on unseen 2017-22):")
for col, q, thr, _, a, b in rows[:12]:
    print(f"  {col:9s} > q{q:.1f} ({thr:6.2f})   2012-16: {s(a)} | 2017-22: {s(b)}")
