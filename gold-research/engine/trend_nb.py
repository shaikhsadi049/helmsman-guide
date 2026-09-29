import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import dyn2_run as R2
m1 = R2.m1
d = m1.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def atr(b, n):
    pc = b.close.shift(); tr = np.maximum(b.high - b.low, np.maximum((b.high - pc).abs(), (b.low - pc).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean()
def rpct(s, n): return s.rolling(n, min_periods=n // 2).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)
T = pd.read_parquet("../trades_v3_reg.parquet"); t = pd.DatetimeIndex(T.time.dt.floor("1D"))
out = {}
for ema in (20, 50, 100):
    for lb in (120, 250, 500):
        f = rpct((d.close - d.close.ewm(span=ema, adjust=False).mean()).abs() / atr(d, 14), lb).shift(1)
        out[f"dt_{ema}_{lb}"] = f.reindex(t).values
pd.DataFrame(out).to_parquet("../dt_variants.parquet")
