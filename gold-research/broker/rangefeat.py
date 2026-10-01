"""Range-regime features on D1 (spot bid bars), known at the previous D1 close; tested as half-lot rules for trend trades."""
import numpy as np, pandas as pd
m = pd.read_parquet("/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/dk/m1_bid.parquet")
D = m.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
D = D[D.index.dayofweek < 5]
h, l, c = D.high, D.low, D.close
tr_ = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(1); atr = tr_.ewm(alpha=1/14).mean()
def since(cond):
    out = np.full(len(cond), np.nan); last = -1
    for i, v in enumerate(cond.values):
        if v: last = i
        out[i] = i - last if last >= 0 else np.nan
    return pd.Series(out, cond.index)
f = pd.DataFrame(index=D.index)
f["since_hi20"] = since(h >= h.rolling(20).max()); f["since_lo20"] = since(l <= l.rolling(20).min())
f["since_ext50"] = np.minimum(since(h >= h.rolling(50).max()), since(l <= l.rolling(50).min()))
e = c.ewm(span=20).mean(); s = np.sign(c - e); f["flips30"] = (s != s.shift()).astype(int).rolling(30).sum()
f["rng30_atr"] = (h.rolling(30).max() - l.rolling(30).min()) / atr
f["pos30"] = (c - l.rolling(30).min()) / (h.rolling(30).max() - l.rolling(30).min())
FEATS = f.shift(1)   # known at today's open = yesterday's close
def at(times, dirs):
    d = pd.DatetimeIndex(times).floor("1D"); j = np.searchsorted(FEATS.index.values, d.values, side="right") - 1
    x = FEATS.iloc[np.clip(j, 0, len(FEATS) - 1)].reset_index(drop=True)
    dirs = np.asarray(dirs)
    out = pd.DataFrame({"since_ext_dir": np.where(dirs == 1, x.since_hi20, x.since_lo20), "since_ext50": x.since_ext50,
                        "flips30": x.flips30, "rng30_atr": x.rng30_atr, "pos30_dir": np.where(dirs == 1, x.pos30, 1 - x.pos30)})
    return out
def past_rank_seq(x, slots):
    out = np.full(len(x), np.nan)
    for s in np.unique(slots):
        ii = np.where(slots == s)[0]
        for k, i in enumerate(ii):
            p = x[ii[:k]]; p = p[np.isfinite(p)]
            if len(p) >= 40 and np.isfinite(x[i]): out[i] = (p < x[i]).mean()
    return out
def test(tr, lab, lo, hi):
    """tr must be sorted by t and contain t, R, slot, dir"""
    import prules as PR
    F = at(tr.t.values, tr.dir.values); trend = tr.slot.str.startswith("S").values; rows = [dict(rule="base", **PR.rep(tr, lab, lo, hi))]
    for c in F.columns:
        rk = past_rank_seq(F[c].values.astype(float), tr.slot.values)
        for q in (0.2, 0.3, 0.4):
            for side in ("low", "high"):
                bad = trend & np.isfinite(rk) & ((rk < q) if side == "low" else (rk > 1 - q))
                d = tr.copy(); d.loc[bad, "R"] *= 0.5; rows.append(dict(rule=f"{c} {side}{int(q*100)}", **PR.rep(d, lab, lo, hi)))
    out = pd.DataFrame(rows)
    out["calmar"] = (out.sumR / out.DD).round(1); return out
