import numpy as np, pandas as pd
T = pd.read_parquet("../trades_v3.parquet")
keep = np.zeros(len(T), bool); busy_until = {}
for i, (s, a, b) in enumerate(zip(T.slot, T.t_in, T.t_out)):
    if busy_until.get(s, -1) < a: keep[i] = True; busy_until[s] = b
X = T[keep].copy(); X["m"] = X.time.dt.tz_localize(None).dt.to_period("M"); X["q"] = X.time.dt.tz_localize(None).dt.to_period("Q")
def st(g):
    w = g.R[g.R > 0].sum(); l = -g.R[g.R < 0].sum()
    return pd.Series({"n": len(g), "win%": round((g.R > 0).mean() * 100), "PF": round(w / l, 2) if l else np.inf, "sumR": round(g.R.sum(), 1), "big>=3R": int((g.R >= 3).sum())})
print("ALL slots by month"); print(X.groupby("m").apply(st).to_string())
print("\nsumR per slot per quarter"); print(X.pivot_table(index="q", columns="slot", values="R", aggfunc="sum").round(1).to_string())
print("\nwin% per slot per quarter"); print((X.assign(w=X.R > 0).pivot_table(index="q", columns="slot", values="w", aggfunc="mean") * 100).round(0).to_string())
# rolling: last 60 trades R mean over time for whole portfolio
X = X.sort_values("time"); X["roll"] = X.R.rolling(100).mean()
print("\nrolling 100-trade mean R at month ends:"); print(X.groupby("m").roll.last().round(2).to_string())
