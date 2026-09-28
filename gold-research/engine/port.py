import numpy as np, pandas as pd, gcdata as G_, strat as S
m1 = G_.load_1m(); GR = {tf: G_.Grid(m1, tf) for tf in ("5min", "15min", "1h")}
SPLIT = pd.Timestamp("2025-08-01", tz="UTC")
S.EXITS["tr6"] = dict(tp_r=[999.0], tp_frac=[1.0], be_leg=0, trail=6.0, brk=False)
def st(tr):
    if len(tr) == 0: return "none"
    p = tr[:, 3]; R = p / tr[:, 4]; gl = -p[p <= 0].sum()
    eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    return f"n={len(tr):3d} win={np.mean(p>0)*100:3.0f}% PF={p[p>0].sum()/gl:.2f} exp={R.mean():+.2f}R tot={R.sum():+6.1f}R DD={dd:4.1f}R"
C = {
 "C1  15m swing brk (old-data pick)": ("15min", dict(entry="swing", adx_min=25, htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=2.0, exit="brk")),
 "C1b 15m swing half (old-data pick)":("15min", dict(entry="swing", adx_min=25, htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=2.0, exit="half:1:0")),
 "P1  1h pullback SL1 trail3":       ("1h",   dict(entry="pullback", htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=1.0, exit="trail:3")),
 "P1b 1h pullback SL1 trail4":       ("1h",   dict(entry="pullback", htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=1.0, exit="trail:4")),
 "P2  15m pullback SL4 trail6":      ("15min", dict(entry="pullback", htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=4.0, exit="tr6")),
 "P2b 15m pullback SL2 half+brk":    ("15min", dict(entry="pullback", htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=2.0, exit="half:1:0")),
 "P3  15m swing SL0.75 brk":         ("15min", dict(entry="swing", htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=0.75, exit="brk")),
 "P4  5m pullback SL2 trail6":       ("5min", dict(entry="pullback", htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=2.0, exit="tr6")),
}
for k, (tf, kw) in C.items():
    tr = G_.backtest(GR[tf], **kw)
    y1 = m1.index[tr[:, 0].astype(int)] < SPLIT
    print(f"{k:36s} Y1: {st(tr[y1])} | Y2: {st(tr[~y1])}")
