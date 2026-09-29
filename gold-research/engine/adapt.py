"""Risk that switches with the situation. S1-S6. Modes combine: drawdown (all-time or rolling peak), market trend score, edge."""
import numpy as np, pandas as pd
T = pd.read_parquet("../trades_v3_reg.parquet"); T = T[T.slot != 6].reset_index(drop=True)
SL = T.slot.values; TI = T.t_in.values; TO = T.t_out.values; TL = T.t_lock.values; ED = T.edge.values
DT = np.nan_to_num(T.d_trend.values, nan=0.5); HE = np.nan_to_num(T.h4_er.values, nan=0.5)
TS = T.time.values.astype("datetime64[m]").astype(np.int64)  # minutes
EV = sorted([(a, 1, i) for i, a in enumerate(TI)] + [(b, 0, i) for i, b in enumerate(TO)])
def sim(R, mx=5, mn=1, fdd=0.2, cap=15, peak_days=0, trend=None, comb="mul", edge=True, start=0, fixed=None):
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set(); hist = []  # (time, eq) for rolling peak
    for t, typ, i in EV:
        if TI[i] < start: continue
        if typ == 0:
            if i in open_:
                eq += open_.pop(i) * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak); hist.append((TS[i], eq))
            continue
        if SL[i] in busy: continue
        if fixed: rp = fixed
        else:
            if peak_days:
                cut = TS[i] - peak_days * 1440
                while hist and hist[0][0] < cut: hist.pop(0)
                rpk = max([e for _, e in hist] + [eq])
                xdd = max(0.0, 1 - (1 - eq / rpk) / fdd)
            else: xdd = max(0.0, 1 - (1 - eq / peak) / fdd)
            xe = (0.5 + 0.5 * np.clip((ED[i] - 0.73) / 1.87, 0, 1)) if edge else 1.0
            if trend is None: x = xdd * xe
            else:
                tr = DT[i] if trend == "d" else HE[i]
                x = max(xdd, tr) * xe if comb == "max" else xdd * xe * (0.5 + 0.5 * tr) if comb == "mul" else (xdd + tr) / 2 * xe
            rp = mn + (mx - mn) * x
        room = eq * cap / 100 - sum(v for j, v in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(eq * rp / 100, room); busy.add(SL[i])
    return eq - 1, mdd
R0 = T.R.values; Rw = np.where(R0 > 0, R0 * .5, R0); Rc = R0 - 1.66 / T.risk.values
starts = [TI[np.searchsorted(T.time.values, np.datetime64(m))] for m in pd.date_range("2025-01-01", "2026-04-01", freq="MS")]
s26 = TI[np.searchsorted(T.time.values, np.datetime64("2026-02-01"))]
def row(name, **kw):
    a = sim(R0, **kw); b = sim(Rw, **kw); c = sim(Rc, **kw); d = sim(R0, start=s26, **kw); e = sim(Rw, start=s26, **kw)
    ws = [sim(Rw, start=s, **kw) for s in starts]
    score = np.log1p(a[0]) / a[1] + np.log1p(b[0]) / b[1]
    print(f"{name:30s} full {a[0]*100:+7,.0f}%/{a[1]*100:2.0f}% | weak {b[0]*100:+5,.0f}%/{b[1]*100:2.0f}% | cost$2 {c[0]*100:+6,.0f}%/{c[1]*100:2.0f}% | "
          f"26-02+ {d[0]*100:+4.0f}%/{d[1]*100:2.0f}% weak {e[0]*100:+4.0f}% | worstDD any start (weak) {max(w[1] for w in ws)*100:2.0f}%", flush=True)
row("fixed 2%", fixed=2); row("fixed 3%", fixed=3)
row("dd*edge 1-5 (now)")
for pdays in (20, 40, 60):
    row(f"rolling peak {pdays}d", peak_days=pdays)
for tr in ("d", "h4"):
    for comb in ("max", "mul", "avg"):
        row(f"trend {tr} {comb}", trend=tr, comb=comb)
for pdays in (20, 40):
    row(f"roll{pdays}d + trend d max", peak_days=pdays, trend="d", comb="max")
    row(f"roll{pdays}d + trend d mul", peak_days=pdays, trend="d", comb="mul")
