import sys; sys.path.insert(0, "../lab")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import lab
M1 = lab.SIG.m1.values; TEND = pd.Timestamp("2026-08-01", tz="UTC")
def taken(slot, spec):
    Rv, Xv, k, rows = np.load(f"tk_{slot}_{spec}.npy"); rows = rows.astype(int); Xv = Xv.astype(int)
    keep = (k > 0) if spec == "recommended" else np.ones(len(rows), bool); ok = keep & np.isfinite(Rv)
    rr = rows[ok]; t = lab.greedy(rr, Xv[ok]); return pd.DataFrame(dict(t=lab.TIME[rr[t]], m=M1[rr[t]], x=Xv[ok][t], R=Rv[ok][t]))
def lot(d, N):
    out = np.ones(len(d)); m, x, R = d.m.values, d.x.values, d.R.values
    for i in range(len(d)):
        c = np.where(x[:i] < m[i])[0][-N:]
        if len(c) == N and R[c].sum() <= 0: out[i] = 0
    return out
def rep(df):
    d = df[(df.t >= lab.D0) & (df.t < TEND)].sort_values("t"); m = lab.metrics(d.R.values, pd.DatetimeIndex(d.t))
    mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
    return dict(sumR=round(m["sumR"], 1), DD=round(m["maxDD_R"], 1), mpos=m["months_pos"], worst=round(mo.min(), 1), sh=round(mo.mean() / mo.std(), 2))
TODAY = [(s, "today", 1) for s in ["S1","S2","S3","S4","S5","S6","F8","F9","F10","F11"]]
MIX = [("S1","today",1),("S2","recommended",1),("S3","recommended",1),("S4","recommended",1),("S5","today",1),("S6","recommended",.5),
       ("S7","recommended",.5),("F8","recommended",1),("F9","recommended",1),("F10","recommended",1),("F11","today",.5)]
for name, legs in (("today", TODAY), ("final_mix", MIX)):
    for N in (0, 10, 20, 30, 40):
        parts = []
        for s, sp, w in legs:
            d = taken(s, sp); d["R"] = d.R * w * (lot(d, N) if N else 1); parts.append(d)
        print(name, N, rep(pd.concat(parts)), flush=True)
