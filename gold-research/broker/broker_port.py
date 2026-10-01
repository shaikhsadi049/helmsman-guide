import sys; sys.path.insert(0, "../lab")
import numpy as np, pandas as pd, pickle, warnings; warnings.filterwarnings("ignore")
import lab
SIG = lab.SIG; F = lab.load_F(); M1 = SIG.m1.values
OUT = pickle.load(open("broker_tick.pkl", "rb"))
TEND = pd.Timestamp("2026-08-01", tz="UTC")
def stream(slot, spec, w=1.0, adx_half=False, skip=None):
    r = OUT[slot]; rows = r["rows"]; R, X = r[spec]; keep = np.isfinite(R)
    if skip == "h4":   # S4: skip H4-stack-disagree signals while past such signals (today's exit) lost on average
        Rb, Xb = r["today"]; bad = r["h4_bad"]
        for i in np.where(bad)[0]:
            past = bad & (Xb < M1[rows[i]]) & np.isfinite(Rb)
            if past.sum() >= 5 and Rb[past].mean() < 0: keep[i] = False
    if skip == "adx": keep &= ~r["adx_bad"]
    rr = rows[keep]; t = lab.greedy(rr, X[keep]); Rk = R[keep][t]
    ww = np.full(len(Rk), w)
    if adx_half: ww = ww * np.where(r["adx_bad"][keep][t], 0.5, 1.0)
    return pd.DataFrame(dict(t=lab.TIME[rr[t]], R=Rk * ww, slot=slot))
def rep(df, lo, hi):
    d = df[(df.t >= lo) & (df.t < hi)].sort_values("t")
    m = lab.metrics(d.R.values, pd.DatetimeIndex(d.t))
    mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
    return dict(sumR=round(m["sumR"], 1), DD=round(m["maxDD_R"], 1), mpos=m["months_pos"], R2=m["eq_R2"], top5=m["top5days_pct"],
                worst=round(mo.min(), 1), sharpe=round(mo.mean() / mo.std(), 2) if len(mo) > 2 else np.nan, n=len(d))
D0 = lab.D0; AUG = pd.Timestamp("2026-09-01", tz="UTC")
PORT = {
 "today": [("S1","today",1),("S2","today",1),("S3","today",1),("S4","today",1),("S5","today",1),("S6","today",1),
           ("F8","today",1),("F9","today",1),("F10","today",1),("F11","today",1)],
 "final_mix(sec12)": [("S1","today",1),("S2","rec",1),("S3","rec",1),("S4","rec",1,False,"h4"),("S5","today",1),("S6","rec",.5),
           ("S7","rec",.5,False,"adx"),("F8","rec",1),("F9","rec",1),("F10","rec",1),("F11","today",.5)],
 "dynamic(f47)": [("S1","today",1),("S2","A3",1,True),("S3","Aq85",1),("S4","B",1),("S5","B",1,True),("S6","A3",.5),
           ("S7","Aq85",.5,True),("F8","rec",1),("F9","rec",1),("F10","rec",1),("F11","today",.5)],
}
rows = []
for name, legs in PORT.items():
    df = pd.concat([stream(*l) for l in legs], ignore_index=True)
    a = rep(df, D0, TEND); b = rep(df, TEND, AUG)
    rows.append(dict(port=name, **a, aug26_R=b["sumR"])); 
    print(name, "per-slot:", df[(df.t >= D0) & (df.t < TEND)].groupby("slot").R.sum().round(1).to_dict())
print(pd.DataFrame(rows).to_string())
# per slot specs incl. ADX half-lot, main window + Aug-26
tab = []
for slot in ["S1","S2","S3","S4","S5","S6","S7"]:
    for spec in ["today", "rec", "A3", "Aq85", "B"]:
        for h in (False, True):
            a = rep(stream(slot, spec, 1, h), D0, TEND); b = rep(stream(slot, spec, 1, h), TEND, AUG)
            tab.append(dict(slot=slot, spec=spec + ("+ADX½" if h else ""), **{k: a[k] for k in ("sumR","DD","mpos","R2","worst")}, aug=b["sumR"]))
    if slot == "S4": a = rep(stream("S4","rec",1,False,"h4"), D0, TEND); tab.append(dict(slot="S4", spec="rec+h4skip", **{k: a[k] for k in ("sumR","DD","mpos","R2","worst")}))
    if slot == "S7": a = rep(stream("S7","rec",1,False,"adx"), D0, TEND); tab.append(dict(slot="S7", spec="rec+adxskip", **{k: a[k] for k in ("sumR","DD","mpos","R2","worst")}))
T = pd.DataFrame(tab); pd.set_option("display.width", 200); print(T.to_string()); T.to_csv("broker_slots.csv", index=False)
