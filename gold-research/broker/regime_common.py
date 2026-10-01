import numpy as np, pandas as pd
CANDS = ["d1_er30", "d1_adx", "d1_rng20_atr", "d1_bbw_rank", "h4_er30", "h4_adx", "h4_rng20_atr", "d1_atr_rank"]
def past_rank(x):
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        p = x[:i]; p = p[np.isfinite(p)]
        if len(p) >= 50 and np.isfinite(x[i]): out[i] = (p < x[i]).mean()
    return out
def ranks(SIG, F, slot, feat):
    rows = np.where(SIG.slot.values == slot)[0]; r = np.full(len(SIG), np.nan); r[rows] = past_rank(F[feat].values[rows]); return r
def evaluate(trades, SIG, F, lab, D0, TEND):
    """trades: DataFrame t, R(weighted), slot, row. Weight trend trades x0.5 when the causal rank of a range feature is in the bottom q."""
    def rep(d):
        d = d[(d.t >= D0) & (d.t < TEND)].sort_values("t"); m = lab.metrics(d.R.values, pd.DatetimeIndex(d.t))
        mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
        return dict(sumR=round(m["sumR"], 1), DD=round(m["maxDD_R"], 1), mpos=m["months_pos"], worst=round(mo.min(), 1), sh=round(mo.mean() / mo.std(), 2))
    out = [dict(rule="base", **rep(trades))]
    tr = trades.slot.str.startswith("S").values
    f8 = trades.copy(); f8.loc[f8.slot == "F8", "R"] *= 0.5; out.append(dict(rule="F8 x0.5", **rep(f8)))
    for feat in CANDS:
        rk = np.full(len(trades), np.nan)
        for s in trades.slot.unique():
            if not s.startswith("S"): continue
            r = ranks(SIG, F, s, feat); m = (trades.slot == s).values; rk[m] = r[trades.row.values[m]]
        for q in (0.2, 0.3, 0.4):
            for lowbad in (True, False):
                bad = tr & np.isfinite(rk) & ((rk < q) if lowbad else (rk > 1 - q))
                d = trades.copy(); d.loc[bad, "R"] *= 0.5
                out.append(dict(rule=f"{feat} {'low' if lowbad else 'high'}{int(q*100)}% x0.5", **rep(d)))
    return pd.DataFrame(out)
