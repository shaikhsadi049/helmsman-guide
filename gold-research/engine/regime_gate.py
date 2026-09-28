"""Regime gates for the runner: decide from slow, causal market-state measures whether trend-following is 'on'."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import engine as E
def gate_features(base):
    """Daily features on the previous closed day, mapped to each bar of `base` (tz-aware index)."""
    d = E.resample(base, "1D")
    c = d.close
    atr = E.atr(d, 14)
    f = pd.DataFrame(index=d.index)
    for n in (20, 60, 120):
        f[f"er{n}"] = (c - c.shift(n)).abs() / c.diff().abs().rolling(n).sum()
    a, _, _ = E.adx(d, 14); f["adxD"] = a
    f["sep"] = (E.ema(c, 50) - E.ema(c, 200)).abs() / atr
    f["dist200"] = (c - E.ema(c, 200)).abs() / atr
    f = f.shift(1)
    key = base.index.normalize()
    return f.reindex(key).set_index(base.index)
def equity_filter(R, n):
    """Take a trade only if the previous n trades (of the unfiltered stream) summed > 0."""
    s = pd.Series(R).rolling(n).sum().shift(1)
    return (s > 0).values | s.isna().values
