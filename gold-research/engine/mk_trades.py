"""Dynamic risk sizing (1%..5%) for EA v3, event-driven with concurrency, open-risk cap and drawdown throttle."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import v3_parity as V, dyn2_run as R2, adv3 as D, adv4, gcdata as G_
idx = R2.idx
rows = []
for si, sl in enumerate(V.SLOTS):
    tf, fam, nc, sess, qsl, qtp, lock, qtr, f1 = sl
    E = V.entries_ea(tf, fam, nc, sess); G = R2.GR[tf]; m = E["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, qsl, 2.0), 0.5, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, qtp, 1.0) / k, 0.1, 3.0); tw = R2.trail_q(m, qtr) * E["atr4"]
    # market-measured edge at signal time: median favourable / median adverse move of the last 60 known signals
    mfe50 = D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, 0.5, 1.0); mae50 = D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, 0.5, 1.0)
    edge = mfe50 / np.maximum(mae50, 1e-6)
    res = adv4.sim_dyn2(m, E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c, R2.G4.mgmt, R2.G4.trend_up, R2.G4.trend_dn,
                        f1 if f1 > 0 else 1e-9, lock, False, G_.COST_RT, 60 * 24 * 30)
    for j in np.where(idx[m] >= R2.S25)[0]:
        rows.append((si, int(m[j]) + 1, int(res[j, 2]), int(res[j, 4]) if res[j, 4] >= 0 else 10**12, res[j, 0], edge[j], risk[j], mfe50[j], mae50[j]))
T = pd.DataFrame(rows, columns=["slot","t_in","t_out","t_lock","R","edge","risk","mfe50","mae50"]).sort_values("t_in").reset_index(drop=True)
T["time"] = idx[T.t_in.values]
T.to_parquet("../trades_v3.parquet"); print(len(T), T.time.min(), T.time.max())
