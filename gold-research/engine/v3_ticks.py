"""Tick-level execution for the 3m slots (S3, S6, S7): same signals and calibration, fills on every GC trade print."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import v3_parity as V, dyn2_run as R2, adv3 as D, adv4, adv as A, gcdata as G_, ticks as T
idx = R2.idx
tk = T.load_ticks("2024-12-15")
ts = tk.ts_event.values.astype("datetime64[ns]").astype(np.int64)
m1_ns = idx.values.astype("datetime64[ns]").astype(np.int64)
mi = np.clip(np.searchsorted(m1_ns, ts, side="right") - 1, 0, len(idx) - 1)
p = tk.price.values + G_.ADJ[mi]
del tk
print("ticks", len(p), flush=True)
# 4H management points and trend state on the tick grid
G4 = R2.G4
end4 = (G4.bars.index + pd.Timedelta("4h")).values.astype("datetime64[ns]").astype(np.int64)
tpos4 = np.searchsorted(ts, end4, side="left") - 1
mg = np.zeros(len(p), bool); ok = tpos4 >= 0; mg[tpos4[ok]] = True
tick_m1 = mi  # each tick's minute -> reuse 1m-grid trend arrays
tu = G4.trend_up[tick_m1]; td = G4.trend_dn[tick_m1]
def tick_run(slot):
    tf, fam, nc, sess, qsl, qtp, lock, qtr, f1 = slot
    Ent = R2.entries(tf, fam, nc, sess); G = R2.GR[tf]; m = Ent["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, Ent["end"], Ent["mae_a"], 60, qsl, 2.0), 0.5, 8.0); risk = k * Ent["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, Ent["end"], Ent["mfe_a"], 60, qtp, 1.0) / k, 0.1, 3.0)
    tw = R2.trail_q(m, qtr) * Ent["atr4"]
    live = np.where(idx[m] >= R2.S25)[0]
    bar_end = (idx[m[live]] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64)
    ent_t = np.searchsorted(ts, bar_end, side="left") - 1          # last tick of the signal bar
    res = adv4.sim_dyn2(ent_t.astype(np.int64), Ent["dir"][live].astype(np.int64), Ent["lvl"][live], risk[live], r1[live], tw[live],
                        p, p, p, p, mg, tu, td, f1 if f1 > 0 else 1e-9, lock, False, G_.COST_RT, 10**9)
    take = A.greedy(ent_t, res[:, 2].astype(np.int64))
    return pd.DataFrame(dict(t_in=idx[m[live][take]], t_out=idx[tick_m1[res[take, 2].astype(int)]], R=res[take, 0]))
for i in (2, 5, 6):
    a = V.run(V.SLOTS[i], False); b = tick_run(V.SLOTS[i])
    print(f"S{i+1} " + V.rep(a, "1-minute engine") + "\n   " + V.rep(b, "TICK engine"), flush=True)
