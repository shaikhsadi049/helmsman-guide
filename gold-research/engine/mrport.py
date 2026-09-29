import numpy as np, pandas as pd, pickle, warnings; warnings.filterwarnings("ignore")
import mr as M, dyn2_run as R2, adv3 as D, adv4, gcdata as G_
idx = R2.idx
MRS = [("15min", "rsi2", "no4h", True), ("1h", "z2", "no4h", False), ("30min", "z2.5", "no4h", False), ("1h", "fbo", "no4h", True)]
def all_signals(tf, fam, regime, sess, qsl=0.7, qtp=0.5, cost=G_.COST_RT):
    E = M.entries(tf, fam, regime, sess); G = R2.GR[tf]; m = E["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, qsl, 2.0), 0.3, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, qtp, 1.0) / k, 0.1, 5.0)
    hor = M.MRH[tf] * int(pd.Timedelta(tf).total_seconds() // 60)
    res = adv4.sim_dyn2(m, E["dir"].astype(np.int64), E["lvl"], risk, r1, np.zeros(len(m)), G.o, G.h, G.l, G.c, R2.G4.mgmt, R2.G4.trend_up, R2.G4.trend_dn, 1.0, 0.0, False, cost, hor)
    s = np.where(idx[m] >= R2.S25)[0]
    return pd.DataFrame(dict(t_in=m[s] + 1, t_out=res[s, 2].astype(np.int64), t_lock=10**12, R=res[s, 0], risk=risk[s], time=idx[m[s]], d_trend=M.dt_at(m[s])))
T = pd.read_parquet("../trades_v3_reg.parquet"); T = T[T.slot != 6][["slot", "t_in", "t_out", "t_lock", "R", "risk", "time", "d_trend"]].copy(); T["kind"] = "trend"
parts = [T]
for j, spec in enumerate(MRS):
    x = all_signals(*spec); x["slot"] = 10 + j; x["kind"] = "mr"; parts.append(x)
    print(spec, len(x))
A_ = pd.concat(parts).sort_values("t_in").reset_index(drop=True); A_["d_trend"] = A_.d_trend.fillna(0.5)
A_.to_parquet("../combo_trades.parquet")
