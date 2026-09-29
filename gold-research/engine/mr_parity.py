import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import mr as M, v3_parity as V, dyn2_run as R2
ATR = {tf: V.sma_atr(R2.GR[tf].bars) for tf in ("15min", "30min", "1h")}
orig_rsi2 = M.rsi2
class FW:  # wrap F to swap atr
    def __init__(s, F, a): s._F = F; s.atr = a
    def __getattr__(s, k): return getattr(s._F, k)
def run_ea(spec, qsl=.7, qtp=.5):
    tf = spec[0]; G = R2.GR[tf]; F0 = G.F
    G.F = FW(F0, ATR[tf]); M.rsi2 = lambda c: V.mt5_rsi(c, 2)
    try: r = M.run(*spec, qsl, qtp)
    finally: G.F = F0; M.rsi2 = orig_rsi2
    return r
def st(r):
    R = r.R.values; w = R > 0; q = r.groupby(r.time.dt.tz_localize(None).dt.to_period("Q")).R.sum()
    return f"n {len(R)} win {w.mean()*100:.0f}% PF {R[w].sum()/-R[~w].sum():.2f} sumR {R.sum():+.1f} q+ {(q>0).sum()}/{len(q)}"
for spec in [("15min", "rsi2", "no4h", True), ("1h", "z2", "no4h", False), ("30min", "z2.5", "no4h", False), ("1h", "fbo", "no4h", True)]:
    print(spec, "| research:", st(M.run(*spec, .7, .5)), "| EA-style:", st(run_ea(spec)))
