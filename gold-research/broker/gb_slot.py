"""Per-strategy giveback study on broker bid/ask ticks, on the EXIT ASSAY USES TODAY.
(1) how often a trade reaches a big floating profit and still closes small; (2) which giveback rule fits each strategy (fixed grid + causal monthly choice)."""
src = open("contagion.py").read()
src = src.replace('LEGS = [("S1","today",1,False),("S2","A3",1,True),("S3","A3",1,False),("S4","B",1,True),("S5","today",1,True),("S6","A3",.5,False),("S7","rec",.5,True)]',
                  'LEGS = [(s, "today", 1, False) for s in ("S1","S2","S3","S4","S5","S6")] + [("S7", "today", 1, False)]')
exec(src.split("def px_at")[0])
COST = 0.07
D0, TEND = lab.D0, pd.Timestamp("2026-08-01", tz="UTC")
live = (pd.to_datetime(T.t.values, utc=True) >= D0) & (pd.to_datetime(T.t.values, utc=True) < TEND)
PATH = []
for i in range(len(T)):
    d = T.dir.values[i]; s0, s1 = np.searchsorted(ts, T.t.values[i]), np.searchsorted(ts, T.tx.values[i])
    p = (BID[s0:s1] if d == 1 else ASK[s0:s1]); PATH.append((((p - T.entry.values[i]) * d - COST) / T.risk.values[i]).astype(np.float32))
mfe = np.array([p.max() if len(p) else 0 for p in PATH]); fin = T.R.values
# (1) giveback statistics on today's exit
rows = []
for slot in sorted(T.slot.unique()):
    m = live & (T.slot.values == slot)
    for lvl in (1, 2, 3):
        hit = m & (mfe >= lvl)
        rows.append(dict(slot=slot, trades=int(m.sum()), reached=f">={lvl}R", n=int(hit.sum()), pct=round(hit.sum() / max(m.sum(), 1) * 100),
                         closed_below_half=round((fin[hit] < 0.5 * mfe[hit]).mean() * 100) if hit.any() else None,
                         closed_below_0_5R=round((fin[hit] < 0.5).mean() * 100) if hit.any() else None,
                         avg_peak=round(mfe[hit].mean(), 2) if hit.any() else None, avg_final=round(fin[hit].mean(), 2) if hit.any() else None))
G = pd.DataFrame(rows); print(G.to_string()); G.to_csv("gb_stats_broker.csv", index=False)
# (2) giveback grid per strategy on top of today's exit: after peak >= a R, exit when open profit < b x peak
A = (0.75, 1.0, 1.5, 2.0, 3.0); Bk = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
def apply(a, b):
    out = fin.copy()
    for i, p in enumerate(PATH):
        if len(p) < 2 or mfe[i] < a: continue
        pk = np.maximum.accumulate(p); hit = np.where((pk >= a) & (p < b * pk))[0]
        if len(hit): out[i] = p[hit[0]]
    return out
GR = {(a, b): apply(a, b) for a in A for b in Bk}
def metr(r, m):
    d = pd.DataFrame(dict(t=pd.to_datetime(T.t.values[m], utc=True), R=r[m])).sort_values("t"); mm = lab.metrics(d.R.values, pd.DatetimeIndex(d.t))
    mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum(); return mm["sumR"], mm["maxDD_R"], (mo > 0).sum(), mo.mean() / mo.std()
res = []
for slot in sorted(T.slot.unique()):
    m = live & (T.slot.values == slot); b0 = metr(fin, m)
    res.append(dict(slot=slot, rule="today (no giveback)", sumR=round(b0[0], 1), DD=round(b0[1], 1), mpos=b0[2], sh=round(b0[3], 2)))
    for (a, b), r in GR.items():
        x = metr(r, m); res.append(dict(slot=slot, rule=f"after {a}R keep {b}", sumR=round(x[0], 1), DD=round(x[1], 1), mpos=x[2], sh=round(x[3], 2)))
    # causal: each month pick the (a,b) with the best sumR/DD on this strategy's trades CLOSED before the month (none if no rule beats today)
    ch = fin.copy(); idxs = np.where(T.slot.values == slot)[0]; tt = pd.to_datetime(T.t.values[idxs], utc=True); tx = pd.to_datetime(T.tx.values[idxs], utc=True)
    for mo in pd.period_range("2025-01", "2026-07", freq="M"):
        st = mo.to_timestamp().tz_localize("UTC"); en = (mo + 1).to_timestamp().tz_localize("UTC")
        past = idxs[tx < st]; cur = idxs[(tt >= st) & (tt < en)]
        if len(past) < 20 or not len(cur): continue
        def sc(r): e = np.cumsum(r[past]); dd = (np.maximum.accumulate(np.r_[0, e])[1:] - e).max(); return e[-1] / max(dd, 1.0)
        best = max(GR, key=lambda k: sc(GR[k]))
        if sc(GR[best]) > sc(fin): ch[cur] = GR[best][cur]
    x = metr(ch, m); res.append(dict(slot=slot, rule="CAUSAL monthly choice", sumR=round(x[0], 1), DD=round(x[1], 1), mpos=x[2], sh=round(x[3], 2)))
R_ = pd.DataFrame(res); R_.to_csv("gb_grid_broker.csv", index=False)
for slot in sorted(T.slot.unique()):
    g = R_[R_.slot == slot]; base = g.iloc[0]; best = g.iloc[1:-1].sort_values("sh", ascending=False).head(3); caus = g.iloc[-1]
    print(slot, "| today:", base.sumR, base.DD, base.mpos, base.sh, "| causal:", caus.sumR, caus.DD, caus.mpos, caus.sh, "| top fixed:", best[["rule", "sumR", "DD", "sh"]].values.tolist())
    nb = g.iloc[1:-1]; print("    grid cells with higher Sharpe than today:", int((nb.sh > base.sh).sum()), "/", len(nb), "| higher sumR:", int((nb.sumR > base.sumR).sum()))
pickle.dump(dict(T=T, mfe=mfe, fin=fin), open("gb_slot_broker.pkl", "wb"))
