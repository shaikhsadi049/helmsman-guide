"""Shadow-book equity filter: a strategy keeps trading on paper always; real lot depends on its own recent paper results (causal)."""
import sys; sys.path.insert(0, "../lab")
import numpy as np, pandas as pd, pickle, warnings; warnings.filterwarnings("ignore")
import lab
SIG = lab.SIG; M1 = SIG.m1.values; OUT = pickle.load(open("broker_tick.pkl", "rb"))
D0 = lab.D0; TEND = pd.Timestamp("2026-08-01", tz="UTC"); AUG = pd.Timestamp("2026-09-01", tz="UTC")
def taken(slot, spec, adx=False):
    r = OUT[slot]; rows = r["rows"]; R, X = r[spec]; ok = np.isfinite(R); rr = rows[ok]; t = lab.greedy(rr, X[ok])
    w = np.where(r["adx_bad"][ok][t], 0.5, 1.0) if adx else np.ones(t.sum())
    return pd.DataFrame(dict(t=lab.TIME[rr[t]], m=M1[rr[t]], x=X[ok][t], R=R[ok][t] * w, slot=slot))
def lot(d, N, mode):
    """lot for each trade from paper results of the last N trades already CLOSED at its entry"""
    out = np.ones(len(d)); m = d.m.values; x = d.x.values; R = d.R.values
    for i in range(len(d)):
        closed = np.where(x[:i] < m[i])[0][-N:]
        if len(closed) < N: continue
        s = R[closed].sum()
        if mode == "off": out[i] = 1.0 if s > 0 else 0.0
        elif mode == "half": out[i] = 1.0 if s > 0 else 0.5
    return out
def rep(df, lo=D0, hi=TEND):
    d = df[(df.t >= lo) & (df.t < hi)].sort_values("t"); m = lab.metrics(d.R.values, pd.DatetimeIndex(d.t))
    mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
    return dict(sumR=round(m["sumR"], 1), DD=round(m["maxDD_R"], 1), mpos=m["months_pos"], R2=m["eq_R2"], worst=round(mo.min(), 1),
                sh=round(mo.mean() / mo.std(), 2) if len(mo) > 2 else np.nan)
CONS = [("S1","today",1,False),("S2","A3",1,True),("S3","A3",1,False),("S4","B",1,True),("S5","today",1,True),("S6","A3",.5,False),
        ("S7","rec",.5,True),("F8","rec",1,False),("F9","rec",1,False),("F10","rec",1,False),("F11","today",.5,False)]
TODAY = [(s,"today",1,False) for s in ["S1","S2","S3","S4","S5","S6","F8","F9","F10","F11"]]
rows = []
for pname, legs in (("today", TODAY), ("consensus", CONS)):
    for N in (0, 5, 10, 15, 20, 30, 40):
        for mode in (("none",) if N == 0 else ("off", "half")):
            parts = []
            for slot, spec, w, adx in legs:
                d = taken(slot, spec, adx); d["R"] = d.R * w * (lot(d, N, mode) if N else 1.0); parts.append(d)
            df = pd.concat(parts, ignore_index=True)
            a = rep(df); b = rep(df, TEND, AUG)
            rows.append(dict(port=pname, N=N, mode=mode, **a, aug=b["sumR"]))
            print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv("eqfilter_port.csv", index=False)
# per slot, consensus spec
ps = []
for slot, spec, w, adx in CONS:
    d = taken(slot, spec, adx)
    for N in (0, 10, 20, 30):
        for mode in (("none",) if N == 0 else ("off", "half")):
            dd = d.copy(); dd["R"] = d.R * (lot(d, N, mode) if N else 1.0); ps.append(dict(slot=slot, N=N, mode=mode, **rep(dd)))
P = pd.DataFrame(ps); pd.set_option("display.width", 200); print(P.to_string()); P.to_csv("eqfilter_slots.csv", index=False)
