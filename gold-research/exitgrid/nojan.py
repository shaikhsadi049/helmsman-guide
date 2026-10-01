"""Per-strategy exit study WITHOUT the late-January-2026 move: every one of 1080 exit combos (stop q x TP x BE x giveback x trail x H1-flip),
each strategy alone (one position at a time), 2025-01..2026-07 minus trades opened 2026-01-26..2026-02-03. usage: python nojan.py broker|comex"""
import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
DATA = sys.argv[1]; S = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad"
sys.path.insert(0, S + ("/dk/lab" if DATA == "broker" else "/lab")); import lab
R = np.load(f"R_{DATA}.npy"); X = np.load(f"X_{DATA}.npy"); rows = np.load(f"rows_{DATA}.npy"); CB = pd.read_csv("combos.csv")
SIG = lab.SIG.iloc[rows].reset_index(drop=True); TIME = pd.DatetimeIndex(SIG.time)
D0, TEND = lab.D0, pd.Timestamp("2026-08-01", tz="UTC"); E0, E1 = pd.Timestamp("2026-01-26", tz="UTC"), pd.Timestamp("2026-02-04", tz="UTC")
out = []
for slot in ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
    ii = np.where((SIG.slot.values == slot) & (TIME >= D0) & (TIME < TEND))[0]
    for j in range(R.shape[1]):
        r = np.nan_to_num(R[ii, j]); t = lab.greedy(rows[ii], X[ii, j]); tt = TIME[ii[t]]; rr = r[t]
        for tag, keep in (("noJan", ~((tt >= E0) & (tt < E1))), ("all", np.ones(len(tt), bool))):
            d = pd.DataFrame(dict(t=tt[keep], R=rr[keep])); mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
            eq = np.cumsum(d.R.values); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max() if len(eq) else 0
            day = d.groupby(d.t.dt.date).R.sum().sort_values(ascending=False)
            out.append(dict(slot=slot, combo=j, tag=tag, n=len(d), sumR=eq[-1] if len(eq) else 0, DD=dd, mpos=int((mo > 0).sum()), nmo=len(mo),
                            sh=mo.mean() / mo.std() if len(mo) > 2 and mo.std() > 0 else 0, top5=day.head(5).sum() / max(eq[-1], 1e-9) if len(eq) else 0))
    print(DATA, slot, "done", flush=True)
O = pd.DataFrame(out); O = O.merge(CB.reset_index().rename(columns={"index": "combo"}), on="combo"); O.to_parquet(f"nojan_{DATA}.parquet")
