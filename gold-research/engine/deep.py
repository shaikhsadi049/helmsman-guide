import numpy as np, pandas as pd
import engine as E, strat as S
pd.set_option("display.width", 250)
m15 = E.load_m15()
D = {"15m": m15, "1h": E.resample(m15, "1h"), "4h": E.resample(m15, "4h")}
FE = {k: S.Feat(v) for k, v in D.items()}
h26 = E.load_h1_2026()
D26 = {"1h": h26, "4h": E.resample(h26, "4h")}
F26 = {k: S.Feat(v) for k, v in D26.items()}

C = {
 "ORIGINAL":        ("15m", dict(entry="flip_alt", sl="pct", sl_val=.25, exit="orig4")),
 "V1 (TradingView)":("15m", dict(entry="swing", adx_min=25, htf=("1h","4h"), sl="atr", sl_val=1.5, exit="orig4_be")),
 "C1 15m trend":    ("15m", dict(entry="swing", adx_min=25, htf=("4h","1D"), sess=(9,22), sl="atr", sl_val=2.0, exit="brk")),
 "C1b 15m half":    ("15m", dict(entry="swing", adx_min=25, htf=("4h","1D"), sess=(9,22), sl="atr", sl_val=2.0, exit="half:1:0")),
 "C2 1h trend":     ("1h",  dict(entry="swing", adx_min=25, htf=("4h","1D"), sess=(9,22), sl="atr", sl_val=1.5, exit="brk")),
 "C2b 1h half":     ("1h",  dict(entry="swing", adx_min=25, htf=("4h","1D"), sess=(9,22), sl="atr", sl_val=1.5, exit="half:1:0")),
 "C3 4h pullback":  ("4h",  dict(entry="pullback", pb_ema=40, htf=("1D",), sl="atr", sl_val=1.5, exit="trail:3")),
 "C3b 4h pb half":  ("4h",  dict(entry="pullback", pb_ema=40, htf=("1D",), sl="atr", sl_val=1.5, exit="half:1:3")),
}
res = {}
for name, (tf, kw) in C.items():
    df = D[tf]; tr = S.backtest(FE[tf], **kw); s = E.stats(tr, df.index)
    R = tr[:,3]/tr[:,4]; yrs = pd.Series(R, index=df.index[tr[:,0].astype(int)].year).groupby(level=0).sum()
    # 2026 holdout (UTC data: shift server-time session by -2h)
    h = ""
    if tf in F26:
        kw2 = dict(kw); 
        if kw2.get("sess"): kw2["sess"] = (kw2["sess"][0]-2, kw2["sess"][1]-2)
        t2 = S.backtest(F26[tf], **kw2)
        if len(t2):
            R2 = t2[:,3]/t2[:,4]; gl = -t2[t2[:,3]<=0,3].sum()
            h = f"2026: n={len(t2)} win={np.mean(t2[:,3]>0)*100:.0f}% PF={t2[t2[:,3]>0,3].sum()/gl if gl>0 else 99:.2f} R={R2.sum():+.1f}"
    # Monte Carlo max DD in R (bootstrap trade order, 1 year of trades)
    rng = np.random.default_rng(0); per = int(s["per_year"]); dds = []
    for _ in range(2000):
        x = rng.choice(R, per); eq = np.cumsum(x); dds.append((np.maximum.accumulate(np.concatenate([[0],eq]))[1:]-eq).max())
    res[name] = s
    print(f"\n### {name} [{tf}] trades={s['trades']} ({s['per_year']:.0f}/yr) win={s['win']:.1f}% PF={s['pf']:.2f} expR={s['expR']:+.3f} totalR={s['totR']:+.0f} DD={s['ddR']:.0f}R  yearsPos={s['years_pos']:.0f}%  long={s['long_R']:+.0f}R short={s['short_R']:+.0f}R")
    print("   per-year R:", " ".join(f"{y}:{v:+.0f}" for y, v in yrs.items()))
    print(f"   MonteCarlo 1-yr DD (R): median {np.median(dds):.1f}, 95th pct {np.percentile(dds,95):.1f}   {h}")
