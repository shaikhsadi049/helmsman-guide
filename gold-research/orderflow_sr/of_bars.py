"""Per-minute order-flow bars from every GC trade print: aggressive buy/sell volume (Databento side B = buyer aggressor,
A = seller aggressor), trade count, large-print volume (size >= 10 lots), VWAP numerator."""
import pyarrow.parquet as pq, numpy as np, pandas as pd, time
D = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/data/gc"
out = []
for y in (2024, 2025, 2026):
    f = pq.ParquetFile(f"{D}/GC_TRADES_{y}.parquet"); t0 = time.time()
    for rg in range(f.num_row_groups):
        t = f.read_row_group(rg, columns=["ts_event", "side", "size", "price"]).to_pandas()
        m = t.ts_event.dt.floor("1min"); sz = t["size"].astype(np.int64); pr = t.price.values
        b = np.where(t.side.values == "B", sz, 0); a = np.where(t.side.values == "A", sz, 0); big = sz >= 10
        g = pd.DataFrame({"m": m.values, "buy": b, "sell": a, "vol": sz, "n": 1, "bigbuy": np.where(big, b, 0), "bigsell": np.where(big, a, 0), "pv": pr * sz})
        out.append(g.groupby("m").sum())
    print(y, f.num_row_groups, "groups", round(time.time() - t0), "s", flush=True)
OF = pd.concat(out).groupby(level=0).sum().sort_index()
OF.index = pd.DatetimeIndex(OF.index).tz_localize("UTC") if OF.index.tz is None else OF.index
OF.to_parquet("of_1m.parquet"); print(OF.shape, OF.index[0], OF.index[-1]); print(OF.describe().T[["mean", "50%", "max"]])
