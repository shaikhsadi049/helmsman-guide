import sys, numpy as np, pandas as pd, pickle, warnings; warnings.filterwarnings("ignore")
DATA = sys.argv[1]; S = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad"
sys.path.insert(0, S + ("/dk/lab" if DATA == "broker" else "/lab")); import lab
NEW = pickle.load(open(f"tick_spec_{DATA}.pkl", "rb")); TEND = pd.Timestamp("2026-08-01", tz="UTC")
E0, E1 = pd.Timestamp("2026-01-26", tz="UTC"), pd.Timestamp("2026-02-04", tz="UTC")
def stream_new(slot, w):
    r = NEW[slot]; ok = np.isfinite(r["R"]); rr = r["rows"][ok]; t = lab.greedy(rr, r["X"][ok]); return pd.DataFrame(dict(t=lab.TIME[rr[t]], R=r["R"][ok][t] * w, slot=slot))
if DATA == "broker":
    OB = pickle.load(open(S + "/dk/of/broker_tick.pkl", "rb"))
    def stream_old(slot, spec, w):
        r = OB[slot]; R, X = r[spec]; ok = np.isfinite(R); rr = r["rows"][ok]; t = lab.greedy(rr, X[ok]); return pd.DataFrame(dict(t=lab.TIME[rr[t]], R=R[ok][t] * w, slot=slot))
    TODAY = lambda s, w=1: stream_old(s, "today", w); FADE = lambda s, w=1: stream_old(s, "rec" if s != "F11" else "today", w)
else:
    def stream_tk(slot, spec, w):
        Rv, Xv, k, rows = np.load(f"{S}/of/tk_{slot}_{spec}.npy"); rows = rows.astype(int); Xv = Xv.astype(int)
        keep = (k > 0) if spec == "recommended" else np.ones(len(rows), bool); ok = keep & np.isfinite(Rv); rr = rows[ok]; t = lab.greedy(rr, Xv[ok])
        return pd.DataFrame(dict(t=lab.TIME[rr[t]], R=Rv[ok][t] * w, slot=slot))
    TODAY = lambda s, w=1: stream_tk(s, "today", w); FADE = lambda s, w=1: stream_tk(s, "recommended" if s != "F11" else "today", w)
def rep(d, nojan):
    d = d[(d.t >= lab.D0) & (d.t < TEND)]
    if nojan: d = d[~((d.t >= E0) & (d.t < E1))]
    d = d.sort_values("t"); mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
    eq = d.R.cumsum().values; dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    day = d.groupby(d.t.dt.date).R.sum().sort_values(ascending=False)
    return dict(R=round(eq[-1], 1), DD=round(dd, 1), mpos=f"{(mo > 0).sum()}/{len(mo)}", worst=round(mo.min(), 1), sh=round(mo.mean() / mo.std(), 2),
                top5=f"{day.head(5).sum() / eq[-1] * 100:.0f}%")
rows = []
for slot in ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
    for nj in (True, False):
        rows.append(dict(slot=slot, Jan="without" if nj else "with", **{f"today_{k}": v for k, v in rep(TODAY(slot), nj).items()},
                         **{f"new_{k}": v for k, v in rep(stream_new(slot, 1), nj).items()}))
T = pd.DataFrame(rows); pd.set_option("display.width", 250); print(T[T.Jan == "without"].drop(columns="Jan").to_string(index=False))
print("\nWITH January:"); print(T[T.Jan == "with"][["slot", "today_R", "today_sh", "new_R", "new_sh"]].to_string(index=False))
FAD = [FADE("F8"), FADE("F9"), FADE("F10"), FADE("F11", .5)]
old = pd.concat([TODAY(s) for s in ["S1", "S2", "S3", "S4", "S5", "S6"]] + [TODAY("F8"), TODAY("F9"), TODAY("F10"), TODAY("F11")])
new = pd.concat([stream_new(s, 1) for s in ["S1", "S2", "S3", "S4", "S5"]] + [stream_new("S6", .5), stream_new("S7", .5)] + FAD)
P = []
for name, d in (("today Assay", old), ("finding-71 exits", new)):
    for nj in (True, False): P.append(dict(portfolio=name, Jan="without" if nj else "with", **rep(d, nj)))
print("\nPORTFOLIO:"); print(pd.DataFrame(P).to_string(index=False))
T.to_csv(f"eval_spec_{DATA}.csv", index=False); pd.DataFrame(P).to_csv(f"eval_port_{DATA}.csv", index=False)
