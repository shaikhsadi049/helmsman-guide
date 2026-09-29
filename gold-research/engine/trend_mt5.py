import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import dyn2_run as R2
d = R2.m1.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
pc = d.close.shift(); tr = np.maximum(d.high - d.low, np.maximum((d.high - pc).abs(), (d.low - pc).abs())); atr = tr.rolling(14).mean()
v = (d.close - d.close.ewm(span=50, adjust=False).mean()).abs() / atr
f = v.rolling(250, min_periods=125).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True).shift(1)
full = pd.read_parquet("../trades_v3_reg.parquet"); t = pd.DatetimeIndex(full.time.dt.floor("1D"))
pd.DataFrame({"mt5": f.reindex(t).values}).to_parquet("../dt_mt5.parquet")
