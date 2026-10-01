import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../bt"); sys.path.insert(0, "..")
import numpy as np, pandas as pd, pickle, warnings; warnings.filterwarnings("ignore")
import lab, dyn2_run as R2, slotw as SW, prules as PR
idx = R2.idx; SIG = lab.SIG; M1 = SIG.m1.values; TD = pickle.load(open("tick_dyn_x.pkl", "rb")); TEND = pd.Timestamp("2026-08-01", tz="UTC")
def tk(slot, spec, w=1.0):
    Rv, Xv, k, rows = np.load(f"tk_{slot}_{spec}.npy"); rows = rows.astype(int); Xv = Xv.astype(int)
    keep = (k > 0) if spec == "recommended" else np.ones(len(rows), bool); ok = keep & np.isfinite(Rv)
    rr = rows[ok]; t = lab.greedy(rr, Xv[ok])
    return pd.DataFrame(dict(t=lab.TIME[rr[t]], tx=idx[np.clip(Xv[ok][t], 0, len(idx) - 1)], R=Rv[ok][t] * w, slot=slot, dir=SIG.dir.values[rr[t]]))
def dyn(slot, spec, adx, w=1.0):
    d = TD[(slot, spec)]; return pd.DataFrame(dict(t=pd.to_datetime(d.t, utc=True), tx=pd.to_datetime(d.tx, utc=True), R=d.R * (d.w if adx else 1) * w, slot=slot, dir=d.dir))
parts = [tk("S1","today"), dyn("S2","A3",True), dyn("S3","A3",False), dyn("S4","B",True), tk("S5","today"), dyn("S6","A3",False,.5),
         tk("S7","recommended",.5)] + [tk(f,"recommended") for f in ("F8","F9","F10")] + [tk("F11","today",.5)]
tr = pd.concat(parts, ignore_index=True); tr["t"] = pd.to_datetime(tr.t, utc=True); tr["tx"] = pd.to_datetime(tr.tx, utc=True)
tr = tr.sort_values("t").reset_index(drop=True); tr.to_parquet("cons_trades_comex.parquet")
r = SW.test(tr, lab, lab.D0, TEND); r.to_csv("slotw_comex.csv", index=False); print(r.to_string())
