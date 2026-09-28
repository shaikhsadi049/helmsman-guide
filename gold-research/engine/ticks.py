"""Tick-level validation: every GC trade print becomes a price step; SL/TP/entries are filled tick by tick."""
import numpy as np, pandas as pd, pyarrow.parquet as pq
import gcdata as G_, strat as S

def load_ticks(start="2024-07-01"):
    parts = []
    for y in (2024, 2025, 2026):
        t = pq.read_table(f"{G_.GC}/GC_TRADES_{y}.parquet", columns=["ts_event", "price", "instrument_id"]).to_pandas()
        parts.append(t)
    t = pd.concat(parts, ignore_index=True)
    t = t[t.ts_event >= pd.Timestamp(start, tz="UTC")].sort_values("ts_event", kind="stable").reset_index(drop=True)
    return t

def adjust(t, m1_rolls):
    """Apply the same Panama back-adjustment as the 1m series (by roll time)."""
    ts = t.ts_event.values
    adj = np.zeros(len(t))
    for when, gap in m1_rolls:
        adj[ts < np.datetime64(when.tz_convert(None))] += gap if False else 0
    return adj

class TickGrid:
    def __init__(self, m1, ticks, tf):
        G = G_.Grid(m1, tf)
        self.G = G
        ts = ticks.ts_event.values.astype("datetime64[ns]").astype(np.int64)
        # back-adjust ticks: the 1m series offset for the minute each tick falls in
        m1_ns = m1.index.values.astype("datetime64[ns]").astype(np.int64)
        mi = np.clip(np.searchsorted(m1_ns, ts, side="right") - 1, 0, len(m1) - 1)
        raw_close = m1.close.values - 0  # adjusted
        self.p = ticks.price.values + G_.ADJ[mi]
        # last tick of each TF bar = signal / management point
        bars = G.bars
        end_ns = (bars.index + pd.Timedelta(tf)).values.astype("datetime64[ns]").astype(np.int64)
        tpos = np.searchsorted(ts, end_ns, side="left") - 1
        ok = tpos >= 0
        self.tpos = tpos
        n = len(ts)
        self.mgmt = np.zeros(n, bool)
        self.mgmt[tpos[ok]] = True
        idx = np.full(n, -1); idx[tpos[ok]] = np.arange(len(tpos))[ok]
        idx = pd.Series(idx).replace(-1, np.nan).ffill().fillna(0).astype(int).values
        self.trend_up = G.F.bull[idx]; self.trend_dn = G.F.bear[idx]; self.atr1 = G.F.atr[idx]
        self.ok = ok
        self.trade_ok = ts >= np.datetime64("2024-08-01").astype("datetime64[ns]").astype(np.int64)
        self.ts = ts

    def place(self, a):
        out = np.zeros(len(self.p), dtype=a.dtype)
        out[self.tpos[self.ok]] = a[self.ok]
        return out

def backtest(TG, entry="swing", adx_min=0, htf=(), sess=None, pb_ema=30, sl="atr", sl_val=2.0, swing_n=8, exit="brk", cost=G_.COST_RT):
    F = TG.G.F
    L, Sg = S.signals(F, entry, adx_min, htf, sess, pb_ema)
    dl, ds = S.stops(F, "swing", swing_n=int(sl_val)) if sl == "swing" else S.stops(F, sl, sl_val)
    x = S.exit_cfg(exit)
    p = TG.p
    return G_.run2(p, p, p, p, TG.place(L) & TG.trade_ok, TG.place(Sg) & TG.trade_ok, TG.trend_up, TG.trend_dn, TG.mgmt,
                   TG.place(dl.astype(float)), TG.place(ds.astype(float)), np.array(x["tp_r"], float), np.array(x["tp_frac"], float),
                   x["be_leg"], x["trail"], TG.atr1, x["brk"], True, cost)
