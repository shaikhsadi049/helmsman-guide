import sys; sys.path.insert(0, "..")
exec(open("eq_comex.py").read().split("TODAY =")[0])
import pickle, regime_common as RC
SIG = lab.SIG; F = lab.load_F(); TD = pickle.load(open("tick_dyn.pkl", "rb"))
def tk(slot, spec):
    Rv, Xv, k, rows = np.load(f"tk_{slot}_{spec}.npy"); rows = rows.astype(int); Xv = Xv.astype(int)
    keep = (k > 0) if spec == "recommended" else np.ones(len(rows), bool); ok = keep & np.isfinite(Rv)
    rr = rows[ok]; t = lab.greedy(rr, Xv[ok]); return pd.DataFrame(dict(t=lab.TIME[rr[t]], R=Rv[ok][t], slot=slot, row=rr[t]))
def dyn(slot, spec, adx):
    d = TD[(slot, spec)]; rs = np.where(SIG.slot.values == slot)[0]; mp = dict(zip(lab.TIME[rs].tz_localize(None) if lab.TIME.tz else lab.TIME[rs], rs))
    return pd.DataFrame(dict(t=pd.DatetimeIndex(d.t).tz_convert("UTC") if pd.DatetimeIndex(d.t).tz else pd.DatetimeIndex(d.t).tz_localize("UTC"), R=(d.R * (d.w if adx else 1)).values, slot=slot, row=[mp[pd.Timestamp(x).tz_localize(None) if pd.Timestamp(x).tz else pd.Timestamp(x)] for x in d.t]))
parts = [tk("S1","today"), dyn("S2","A3",True), dyn("S3","A3",False), dyn("S4","B",True), tk("S5","today"),
         dyn("S6","A3",False).assign(R=lambda x: x.R*.5), tk("S7","recommended").assign(R=lambda x: x.R*.5)]
parts += [tk(f,"recommended") for f in ("F8","F9","F10")] + [tk("F11","today").assign(R=lambda x: x.R*.5)]
tr = pd.concat(parts, ignore_index=True); tr["t"] = pd.to_datetime(tr.t, utc=True)
res = RC.evaluate(tr, SIG, F, lab, lab.D0, TEND); res.to_csv("regime_comex.csv", index=False); print(res.to_string())
