"""USD strength proxy from EURUSD 1m (HistData, New York time) aligned to the GC 1m grid."""
import numpy as np, pandas as pd
import engine as E
FX = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/data/fx"
END = pd.Timestamp("2025-12-31", tz="UTC")

def load_usd():
    d = pd.concat([pd.read_csv(f"{FX}/EURUSD_{y}.csv", sep=";", header=None, names=["t","o","h","l","c","v"]) for y in (2023, 2024, 2025)])
    # verified by lead/lag against GC: timestamps are New York local time (with DST)
    t = pd.to_datetime(d.t, format="%Y%m%d %H%M%S").dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    keep = t.notna().values
    s = pd.DataFrame({"open": 1 / d.o.values[keep], "high": 1 / d.l.values[keep], "low": 1 / d.h.values[keep], "close": 1 / d.c.values[keep]},
                     index=pd.DatetimeIndex(t[keep]).tz_convert("UTC")).sort_index()
    return s[~s.index.duplicated()]

class USD:
    def __init__(self, m1_index):
        u = load_usd()
        self.u = u
        self.m1_index = m1_index
        c = u.close.reindex(m1_index, method="ffill", limit=30)
        self.close_m1 = c.values
        self.avail = (m1_index <= END) & ~np.isnan(self.close_m1)
        self.cache = {}

    def htf_up(self, rule, fast=20, slow=50):
        """USD rising on the previous closed `rule` bar (EMA fast > slow), mapped to the GC 1m grid."""
        key = ("htf", rule, fast, slow)
        if key not in self.cache:
            b = E.resample(self.u, rule)
            up = (E.ema(b.close, fast) > E.ema(b.close, slow)).shift(1)
            k = self.m1_index.floor(rule)
            self.cache[key] = pd.Series(up.reindex(k).values, index=self.m1_index).astype("float").values
        return self.cache[key]

    def stack(self, rule):
        """USD 6-EMA stack (30..60) on `rule`, previous closed bar: +1 bull, -1 bear, 0 mixed."""
        key = ("stack", rule)
        if key not in self.cache:
            b = E.resample(self.u, rule); c = b.close
            e = {n: E.ema(c, n) for n in (30, 35, 40, 45, 50, 60)}
            bull = (e[30] > e[35]) & (e[35] > e[40]) & (e[40] > e[45]) & (e[45] > e[50]) & (e[50] > e[60])
            bear = (e[30] < e[35]) & (e[35] < e[40]) & (e[40] < e[45]) & (e[45] < e[50]) & (e[50] < e[60])
            st = (bull.astype(int) - bear.astype(int)).shift(1)
            k = self.m1_index.floor(rule)
            self.cache[key] = pd.Series(st.reindex(k).values, index=self.m1_index).values
        return self.cache[key]

    def corr(self, gold_close_m1, rule="1h", n=120):
        """Rolling correlation of gold vs USD returns on `rule` bars (previous closed bar)."""
        key = ("corr", rule, n)
        if key not in self.cache:
            g = pd.Series(gold_close_m1, index=self.m1_index).resample(rule).last().dropna()
            u = self.u.close.resample(rule).last().reindex(g.index).ffill()
            rc = np.log(g).diff().rolling(n, min_periods=n // 2).corr(np.log(u).diff()).shift(1)
            full = rc.reindex(pd.date_range(rc.index[0], rc.index[-1], freq=rule)).ffill()
            self.cache[key] = pd.Series(full.reindex(self.m1_index.floor(rule)).values, index=self.m1_index).values
        return self.cache[key]
