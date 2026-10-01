"""Portfolio-level causal rules to cut drawdowns. trades: t (entry), tx (exit), R (already weighted), slot, dir."""
import numpy as np, pandas as pd
def apply(tr, rule, p):
    tr = tr.sort_values("t").reset_index(drop=True); w = np.ones(len(tr)); t = tr.t.values; tx = tr.tx.values; R = tr.R.values
    trend = tr.slot.str.startswith("S").values; d = tr.dir.values
    for i in range(len(tr)):
        if rule in ("cap", "capdir", "caphalf") and trend[i]:
            op = (t[:i] < t[i]) & (tx[:i] > t[i]) & trend[:i] & (w[:i] > 0)
            if rule == "capdir": op &= d[:i] == d[i]
            if op.sum() >= p: w[i] = 0.5 if rule == "caphalf" else 0.0
        elif rule in ("day", "week"):
            per = "D" if rule == "day" else "W"
            cur = pd.Timestamp(t[i]).to_period(per)
            done = (tx[:i] < t[i]); same = np.array([pd.Timestamp(x).to_period(per) == cur for x in tx[:i]]) if i else np.zeros(0, bool)
            if i and (R[:i] * w[:i])[done & same].sum() <= -p: w[i] = 0.0
        elif rule == "ddhalf":
            done = tx[:i] < t[i]
            if done.any():
                o = np.argsort(tx[:i][done]); eq = np.cumsum((R[:i] * w[:i])[done][o])
                if eq.max(initial=0) - eq[-1] > p: w[i] = 0.5
    out = tr.copy(); out["R"] = R * w; return out
def rep(d, lab, lo, hi):
    d = d[(d.t >= lo) & (d.t < hi)].sort_values("t"); m = lab.metrics(d.R.values, pd.DatetimeIndex(d.t))
    mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
    s25 = d[(d.t >= pd.Timestamp("2025-05-01", tz="UTC")) & (d.t < pd.Timestamp("2025-09-01", tz="UTC"))].R.sum()
    return dict(sumR=round(m["sumR"], 1), DD=round(m["maxDD_R"], 1), mpos=m["months_pos"], worst=round(mo.min(), 1),
                sh=round(mo.mean() / mo.std(), 2), summer25=round(s25, 1))
GRID = [("base", 0)] + [("cap", k) for k in (2, 3, 4, 5)] + [("capdir", k) for k in (2, 3, 4)] + [("caphalf", k) for k in (2, 3, 4)] + \
       [("day", L) for L in (2, 3, 5)] + [("week", L) for L in (4, 6, 10)] + [("ddhalf", D) for D in (6, 10, 15)]
def run_all(tr, lab, lo, hi):
    rows = []
    for rule, p in GRID:
        d = tr if rule == "base" else apply(tr, rule, p); rows.append(dict(rule=f"{rule} {p}", **rep(d, lab, lo, hi))); print(rows[-1], flush=True)
    return pd.DataFrame(rows)
