import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../..")
import pandas as pd, lab, rangefeat as RF
tr = pd.read_parquet("cons_trades_broker.parquet").sort_values("t").reset_index(drop=True)
r = RF.test(tr, lab, lab.D0, pd.Timestamp("2026-08-01", tz="UTC")); r.to_csv("range_broker.csv", index=False); print(r.to_string())
