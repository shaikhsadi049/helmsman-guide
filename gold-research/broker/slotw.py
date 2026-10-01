"""Causal monthly slot weights: each month, weights from the slot's own closed-trade results before the month (with 2024 H2 warm-up)."""
import numpy as np, pandas as pd
def weights(tr, scheme, look):
    tr = tr.copy(); tr["mo"] = tr.t.dt.tz_localize(None).dt.to_period("M"); w = np.ones(len(tr))
    for mo in sorted(tr.mo.unique()):
        start = mo.to_timestamp().tz_localize("UTC"); lo = (mo - look).to_timestamp().tz_localize("UTC")
        cur = (tr.mo == mo).values; ws = {}
        for s in tr.slot.unique():
            p = tr[(tr.slot == s) & (tr.tx < start) & (tr.t >= lo)]
            if len(p) < 10: ws[s] = 1.0; continue
            mr = p.groupby(p.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
            if scheme == "invvol": ws[s] = 1.0 / max(p.R.std() * np.sqrt(len(p) / look), 1e-6)
            elif scheme == "invdd":
                eq = p.sort_values("tx").R.cumsum().values; dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max(); ws[s] = 1.0 / max(dd, 1.0)
            elif scheme == "quality":
                eq = p.sort_values("tx").R.cumsum().values; dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max(); ws[s] = np.clip(eq[-1] / max(dd, 1.0), 0.25, 3)
        trend = [s for s in ws]; mean = np.mean([ws[s] for s in trend])
        for s in ws:
            m = cur & (tr.slot == s).values; w[m] = np.clip(ws[s] / mean, 0.25, 2.0)
    out = tr.drop(columns="mo"); out["R"] = out.R * w; return out
def test(tr, lab, lo, hi):
    import prules as PR
    rows = [dict(rule="base", **PR.rep(tr, lab, lo, hi))]
    for sch in ("invvol", "invdd", "quality"):
        for look in (3, 6, 9):
            rows.append(dict(rule=f"{sch} {look}m", **PR.rep(weights(tr, sch, look), lab, lo, hi)))
    o = pd.DataFrame(rows); o["calmar"] = (o.sumR / o.DD).round(1); return o
