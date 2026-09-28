import numpy as np, pandas as pd, gcdata as G_, strat as S
exec(open("port.py").read().split("for k, (tf, kw)")[0])
S.EXITS["h1tr3"] = dict(tp_r=[1.0, 999.0], tp_frac=[.5, .5], be_leg=1, trail=3.0, brk=False)
C["P1h 1h pullback SL1 half+trail3"] = ("1h", dict(entry="pullback", htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=1.0, exit="h1tr3"))
C["P2h 15m pullback SL4 half+trail6"] = ("15min", dict(entry="pullback", htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=4.0, exit="half:1:6"))
streams = {}
for k in ["C1b 15m swing half (old-data pick)", "P1  1h pullback SL1 trail3", "P1h 1h pullback SL1 half+trail3", "P2  15m pullback SL4 trail6", "P2h 15m pullback SL4 half+trail6", "C1  15m swing brk (old-data pick)"]:
    tf, kw = C[k]; tr = G_.backtest(GR[tf], **kw)
    R = tr[:, 3] / tr[:, 4]; t = m1.index[tr[:, 1].astype(int)]
    streams[k] = pd.Series(R, index=t)
    y1 = t < SPLIT
    print(f"{k:36s} Y1: {st(tr[y1])} | Y2: {st(tr[~y1])}")
def port(names, w=None):
    s = pd.concat([streams[n] for n in names]).sort_index()
    eq = s.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    mo = s.groupby(pd.Grouper(freq="ME")).sum()
    return f"trades/yr={len(s)/2:.0f} win={(s>0).mean()*100:.0f}% totR={s.sum():+.0f} DD={dd:.1f}R months+={(mo>0).mean()*100:.0f}% worst month={mo.min():+.1f}R"
print("\nPORTFOLIO (each strategy trades independently, same risk per trade):")
print(" A: C1b + P1h + P2h (high win-rate set):", port(["C1b 15m swing half (old-data pick)", "P1h 1h pullback SL1 half+trail3", "P2h 15m pullback SL4 half+trail6"]))
print(" B: C1  + P1  + P2  (max-profit set)   :", port(["C1  15m swing brk (old-data pick)", "P1  1h pullback SL1 trail3", "P2  15m pullback SL4 trail6"]))
