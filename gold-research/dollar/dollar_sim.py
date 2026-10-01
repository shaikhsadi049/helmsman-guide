"""Account simulation in dollars: every signal in time order, one position per slot, broker lot rules (0.01 min/step), min-lot stretch,
open-risk cap 15%, max 10 positions, fades x0.5 risk. Balance-based equity (floating P&L ignored -> slightly optimistic for the EA's throttle)."""
import sys; sys.path.insert(0, "../lab")
import numpy as np, pandas as pd, pickle, warnings; warnings.filterwarnings("ignore")
import lab
SIG = lab.SIG; D = pickle.load(open("dollar_trades.pkl", "rb"))
idx = pd.DatetimeIndex(pd.read_parquet("../m1_bid.parquet", columns=["close"]).index)
m = pd.read_parquet("../m1_bid.parquet"); d1 = m.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna(); d1 = d1[d1.index.dayofweek < 5]
import talib
e = talib.EMA(d1.close.values, 50); a = talib.ATR(d1.high.values, d1.low.values, d1.close.values, 14); v = np.abs(d1.close.values - e) / a
ts_ = pd.Series(v).rolling(250, min_periods=125).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True).values
TS = pd.Series(ts_, d1.index).shift(1).fillna(0.5)                      # trend score known at the day's open
def tscore(t): return float(TS.iloc[max(np.searchsorted(TS.index.values, t.floor("1D").to_datetime64(), side="right") - 1, 0)])
def events(exitv):
    ev = []
    for slot, r in D.items():
        R, X, risk = r[exitv]; rows = r["rows"]
        for k, i in enumerate(rows):
            if not np.isfinite(R[k]): continue
            ev.append((idx[SIG.m1.values[i] + 1], idx[min(int(X[k]) + 1, len(idx) - 1)], slot, float(R[k]), float(risk[k])))
    return sorted(ev)
def run(exitv, mode, start, end, bal0=1000.0, maxr=5.0, minr=1.0, fdd=20.0, stretch=2.0, cap=15.0):
    bal = bal0; peak = bal0; openp = []; busy = {}; out = []
    for tin, tout, slot, R, risk in EV[exitv]:
        if tin < start or tin >= end: continue
        for p in [p for p in openp if p[0] <= tin]:
            bal += p[1]; out.append((p[0], p[1])); openp.remove(p); peak = max(peak, bal)
        if busy.get(slot, start) > tin or len(openp) >= 10: continue
        fade = slot.startswith("F"); x = tscore(tin); x = 1 - x if fade else x
        dd = 1 - bal / peak
        if mode == "EA":        rp = minr + (maxr - minr) * max(0.0, 1 - dd * 100 / fdd) * x
        elif mode == "EA_noDD": rp = minr + (maxr - minr) * x
        else:                   rp = float(mode)
        if fade: rp *= 0.5
        lots = np.floor(bal * rp / 100 / (risk * 100) / 0.01 + 1e-9) * 0.01
        if lots <= 0:
            if fade or stretch <= 0 or risk * 1.0 > bal * stretch / 100: continue
            lots = 0.01
        room = bal * cap / 100 - sum(p[2] for p in openp)
        if risk * lots * 100 > room:
            lots = np.floor(room / (risk * 100) / 0.01) * 0.01
            if lots <= 0: continue
        pnl = R * risk * lots * 100; openp.append((tout, pnl, risk * lots * 100)); busy[slot] = tout
    for p in openp: bal += p[1]; out.append((p[0], p[1]))
    o = pd.DataFrame(out, columns=["t", "pnl"]).sort_values("t")
    eq = bal0 + o.pnl.cumsum().values; pk = np.maximum.accumulate(np.r_[bal0, eq])[1:]; mdd = ((pk - eq) / pk).max() * 100
    mo = o.groupby(o.t.dt.tz_localize(None).dt.to_period("M")).pnl.sum()
    jan = o[(o.t >= "2026-01-01") & (o.t < "2026-02-01")].pnl.sum()
    return dict(final=round(bal), maxDD_pct=round(mdd, 1), months_pos=f"{(mo > 0).sum()}/{len(mo)}", jan26=round(jan),
                feb_aug26=round(o[(o.t >= "2026-02-01") & (o.t < "2026-09-01")].pnl.sum()), trades=len(o)), mo
EV = {k: events(k) for k in ("E0_today_minlot", "E1_mode1_be", "E2_3R_be", "E3_3R_be_gb")}
S26, S25, END = pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC")
rows = []; MO = {}
for ex in EV:
    for mode, kw, name in [("EA", {}, "EA now: 1-5%, throttle 20%"), ("EA", dict(stretch=0), "EA now, no min-lot stretch"),
                           ("EA_noDD", dict(maxr=2.0), "1-2% by trend, no throttle"), ("1", {}, "fixed 1%"), ("2", {}, "fixed 2%")]:
        for st, lab_ in ((S26, "2026 from $1k"), (S25, "2025-26 from $1k")):
            r, mo = run(ex, mode, st, END, **kw); rows.append(dict(exit=ex, money=name, period=lab_, **r)); MO[(ex, name, lab_)] = mo
            print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv("dollar_sim.csv", index=False); pickle.dump(MO, open("dollar_months.pkl", "wb"))
