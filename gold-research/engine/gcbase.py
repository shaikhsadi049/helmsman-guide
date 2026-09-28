import time, numpy as np, pandas as pd, gcdata as G_, engine as E
t=time.time(); m1=G_.load_1m(); print("1m", len(m1), round(time.time()-t,1),"s")
GR={tf:G_.Grid(m1,tf) for tf in ("15min","1h","4h")}
print("grids", round(time.time()-t,1))
def st(tr, idx):
    if len(tr)==0: return "no trades"
    p=tr[:,3]; R=p/tr[:,4]; gl=-p[p<=0].sum()
    eq=np.cumsum(R); dd=(np.maximum.accumulate(np.concatenate([[0],eq]))[1:]-eq).max()
    q=pd.Series(R,index=idx[tr[:,0].astype(int)]).groupby(pd.Grouper(freq="QE")).sum()
    return f"n={len(tr)} win={np.mean(p>0)*100:.0f}% PF={p[p>0].sum()/gl:.2f} expR={R.mean():+.3f} totR={R.sum():+.1f} DD={dd:.1f}R | quarters: "+" ".join(f"{v:+.0f}" for v in q.values)
C = {
 "ORIGINAL 15m":  ("15min", dict(entry="flip_alt", sl="pct", sl_val=.25, exit="orig4")),
 "V1 15m":        ("15min", dict(entry="swing", adx_min=25, htf=("1h","4h"), sl="atr", sl_val=1.5, exit="orig4_be")),
 "C1 15m":        ("15min", dict(entry="swing", adx_min=25, htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=2.0, exit="brk")),
 "C1b 15m":       ("15min", dict(entry="swing", adx_min=25, htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=2.0, exit="half:1:0")),
 "C2 1h":         ("1h",   dict(entry="swing", adx_min=25, htf=("4h","1D"), sess=(7,20), sl="atr", sl_val=1.5, exit="brk")),
 "C3 4h":         ("4h",   dict(entry="pullback", pb_ema=40, htf=("1D",), sl="atr", sl_val=1.5, exit="trail:3")),
 "C3b 4h":        ("4h",   dict(entry="pullback", pb_ema=40, htf=("1D",), sl="atr", sl_val=1.5, exit="half:1:3")),
}
for k,(tf,kw) in C.items():
    tr=G_.backtest(GR[tf], **kw); print(f"{k:14s}", st(tr, m1.index))
print("total", round(time.time()-t,1))
