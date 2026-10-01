"""How to USE the ADX threshold dynamically: skip vs. size-down vs. causal-learned threshold; per slot and portfolio (equal weights)."""
import sys, numpy as np, pandas as pd, pickle, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "../lab"); import lab
D = pickle.load(open("dyn_deep_res.pkl", "rb")); MS = lab._ms()
def run(slot, mode, thr=0.8, w_bad=0.25):
    d = D[slot]; rows, R, X, m = d["rows"], d["R"], d["X"], d["m"]; p = d["pr"]["ADX(H1)"]
    bad = np.nan_to_num(p, nan=0) > thr; w = np.ones(len(rows)); keep = np.ones(len(rows), bool)
    if mode == "skip": keep = ~bad
    elif mode == "size": w = np.where(bad, w_bad, 1.0)
    elif mode == "learned":                # each month choose threshold in {none,.7,.8,.9} by past pooled-over-slots skip results
        keep = np.ones(len(rows), bool)
        for a, b in zip(MS[:-1], MS[1:]):
            t = (m >= a) & (m < b)
            if not t.any(): continue
            best, bt = -1e9, None
            for th in (None, 0.7, 0.8, 0.9):
                tot = 0.0
                for sl, dd in D.items():
                    past = dd["X"] < a; pp = np.nan_to_num(dd["pr"]["ADX(H1)"], nan=0)
                    kk = past if th is None else past & (pp <= th)
                    tot += np.clip(dd["R"][kk], -1.5, 5).sum() / max(past.sum(), 1)
                if tot > best: best, bt = tot, th
            if bt is not None: keep[t] = ~(np.nan_to_num(p[t], nan=0) > bt)
    live = keep & (lab.TIME[rows] >= lab.D0); rr = rows[live]; tk = lab.greedy(rr, X[live])
    return pd.DataFrame(dict(R=R[live][tk] * w[live][tk], t=lab.TIME[rr[tk]]))
def rep(df):
    m = lab.metrics(df.R.values, df.t); mon = df.groupby(pd.DatetimeIndex(df.t).tz_localize(None).to_period("M")).R.sum()
    return f"{m['sumR']:+6.1f}R DD {m['maxDD_R']:4.1f} m+ {m['months_pos']} R2 {m['eq_R2']} top5 {m['top5days_pct']}% mSharpe {mon.mean()/mon.std():.2f}"
modes = [("none", {}), ("skip >0.8", dict(mode="skip")), ("size x0.25 >0.8", dict(mode="size")), ("size x0.5 >0.8", dict(mode="size", w_bad=0.5)),
         ("skip >0.9", dict(mode="skip", thr=0.9)), ("skip >0.7", dict(mode="skip", thr=0.7)), ("learned threshold (causal)", dict(mode="learned"))]
for name, kw in modes:
    kw = dict(mode="none", **kw) if "mode" not in kw else kw
    parts = [run(s, **kw) for s in D]
    print(f"PORTFOLIO {name:28s} " + rep(pd.concat(parts)))
    if name in ("none", "skip >0.8", "size x0.5 >0.8", "learned threshold (causal)"):
        for s, df in zip(D, parts): print(f"     {s}: " + rep(df))
