"""Exit overlays on the consensus trend trades, tick by tick (broker bid/ask). Only EARLIER exits are added, so the original path stays valid until the overlay fires."""
exec(open("contagion.py").read().split("def px_at")[0])
import talib
m1 = pd.read_parquet("../m1_bid.parquet")
def bars(rule):
    b = m1.resample(rule, label="left", closed="left").agg({"close": "last"}).dropna(); ct = (b.index + pd.Timedelta(rule)).values.astype("datetime64[ns]").astype(np.int64)
    return b.close.values, ct
TR = {}
for tf in ("1h", "4h"):
    c, ct = bars(tf)
    for n in (20, 50):
        e = talib.EMA(c, n); TR[f"{tf} close vs EMA{n}"] = (ct, c < e, c > e)   # long-bad, short-bad at bar close
    e1, e2 = talib.EMA(c, 20), talib.EMA(c, 50); TR[f"{tf} EMA20 x EMA50"] = (ct, e1 < e2, e1 > e2)
COST = 0.07
def overlay(kind, a=None, b=None):
    newR = T.R.values.copy()
    for i in range(len(T)):
        d = T.dir.values[i]; e = T.entry.values[i]; rk = T.risk.values[i]
        s0, s1 = np.searchsorted(ts, T.t.values[i]), np.searchsorted(ts, T.tx.values[i])
        if s1 - s0 < 2: continue
        p = BID[s0:s1] if d == 1 else ASK[s0:s1]; fav = BID[s0:s1] if d == 1 else ASK[s0:s1]
        r = ((p - e) * d - COST) / rk
        if kind == "giveback":            # after peak >= a R, exit when open profit falls below b x peak
            peak = np.maximum.accumulate(r); hit = np.where((peak >= a) & (r < b * peak))[0]
            if len(hit): newR[i] = r[hit[0]]
        elif kind == "trend":             # exit at the first tick after a bar close where the trend flipped against the trade
            ct, lb, sb = TR[a]; bad = lb if d == 1 else sb
            j0, j1 = np.searchsorted(ct, T.t.values[i], side="right"), np.searchsorted(ct, T.tx.values[i], side="left")
            k = np.where(bad[j0:j1])[0]
            if len(k):
                tt = ct[j0 + k[0]]; q = np.searchsorted(ts, tt) - s0
                if 0 <= q < len(r): newR[i] = r[q]
        elif kind == "trend_if_profit":   # same, but only if the trade is in profit at that moment
            ct, lb, sb = TR[a]; bad = lb if d == 1 else sb
            j0, j1 = np.searchsorted(ct, T.t.values[i], side="right"), np.searchsorted(ct, T.tx.values[i], side="left")
            for k in np.where(bad[j0:j1])[0]:
                q = np.searchsorted(ts, ct[j0 + k]) - s0
                if 0 <= q < len(r) and r[q] > 0: newR[i] = r[q]; break
    out = pd.DataFrame(dict(t=pd.to_datetime(T.t.values, utc=True), R=newR * T.w.values, slot=T.slot.values))
    z = pd.concat([out, FR], ignore_index=True); z["t"] = pd.to_datetime(z.t, utc=True); return z, newR
D0, TEND = lab.D0, pd.Timestamp("2026-08-01", tz="UTC")
res = []; per = {}
specs = [("base", None, None, None)] + [("giveback", a, b, f"giveback peak>={a}R keep {b}") for a in (1.0, 1.5, 2.0, 3.0) for b in (0.4, 0.5, 0.6, 0.7)] + \
        [("trend", n, None, f"trend flip: {n}") for n in TR] + [("trend_if_profit", n, None, f"trend flip (in profit): {n}") for n in TR]
for kind, a, b, name in specs:
    if kind == "base": z, nr = overlay("none")
    else: z, nr = overlay(kind, a, b)
    r = PR.rep(z, lab, D0, TEND); r["calmar"] = round(r["sumR"] / r["DD"], 1); res.append(dict(rule=name or "base", **r)); print(res[-1], flush=True)
    per[name or "base"] = pd.Series(nr * T.w.values).groupby(T.slot.values).sum().round(1).to_dict()
pd.DataFrame(res).to_csv("overlay_broker.csv", index=False); pd.DataFrame(per).T.to_csv("overlay_broker_slots.csv")
