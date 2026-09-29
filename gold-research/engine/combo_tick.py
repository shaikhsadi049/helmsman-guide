import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
exec(open("mr_ticks.py").read().split("def rep(")[0].replace("@njit(cache=True)", "@njit"))
A_ = pd.read_parquet("../combo_trades.parquet")
parts = [A_[A_.kind == "trend"]]
for j, spec in enumerate([("15min", "rsi2", "no4h", True), ("1h", "z2", "no4h", False), ("30min", "z2.5", "no4h", False), ("1h", "fbo", "no4h", True)]):
    tf = spec[0]; E = M.entries(*spec); m = E["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, .7, 2.0), 0.3, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, .5, 1.0) / k, 0.1, 5.0)
    live = np.where(idx[m] >= R2.S25)[0]
    bar_end = (idx[m[live]] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64)
    ent_t = np.searchsorted(ts, bar_end, side="left") - 1
    end_t = np.searchsorted(ts, bar_end + M.MRH[tf] * int(pd.Timedelta(tf).total_seconds()) * 10**9, side="left")
    res = tick_fade(ent_t.astype(np.int64), end_t.astype(np.int64), E["dir"][live].astype(np.int64), E["lvl"][live], risk[live], r1[live], p, G_.COST_RT, False)
    old = A_[A_.slot == 10 + j].reset_index(drop=True)
    assert len(old) == len(live), (len(old), len(live))
    new = old.copy(); new["R"] = res[:, 0]; new["t_out"] = mi[res[:, 1].astype(np.int64)] + 1
    print(spec, "1m sum(all signals)", round(old.R.sum(), 1), "tick", round(np.nansum(res[:, 0]), 1), flush=True)
    parts.append(new)
B = pd.concat(parts).sort_values("t_in").reset_index(drop=True); B["R"] = B.R.fillna(0)
B.to_parquet("../combo_trades_tick.parquet")
