import numpy as np, pandas as pd
T = pd.read_parquet("../trades_v3_reg.parquet")
SL = T.slot.values; TI = T.t_in.values; TO = T.t_out.values; TL = T.t_lock.values; ED = T.edge.values; DT = T.d_trend.values
EV = sorted([(a, 1, i) for i, a in enumerate(TI)] + [(b, 0, i) for i, b in enumerate(TO)])
def sim(R, mx=5, mn=1, full_dd=0.2, cap=15, eqn=0, eqlow=0.0, use_edge=True, dtr=False, start=0):
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set(); ema = None; a = 2 / (eqn + 1) if eqn else 0; n = 0
    for t, typ, i in EV:
        if TI[i] < start: continue
        if typ == 0:
            if i in open_:
                eq += open_.pop(i) * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
                ema = eq if ema is None else ema + a * (eq - ema); n += 1
            continue
        if SL[i] in busy: continue
        x = max(0.0, 1 - (1 - eq / peak) / full_dd)
        if use_edge: x *= 0.5 + 0.5 * np.clip((ED[i] - 0.73) / 1.87, 0, 1)
        if dtr and not np.isnan(DT[i]): x *= 0.5 + 0.5 * DT[i]
        if eqn and n >= eqn and eq < ema: x *= eqlow
        amt = eq * (mn + (mx - mn) * x) / 100
        room = eq * cap / 100 - sum(v for j, v in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(amt, room); busy.add(SL[i])
    return eq - 1, mdd
R0 = T.R.values; Rw = np.where(R0 > 0, R0 * .5, R0); Rc = R0 - 1.66 / T.risk.values
starts = [TI[np.searchsorted(T.time.values, np.datetime64(m))] for m in pd.date_range("2025-01-01", "2026-04-01", freq="MS")]
def row(name, **kw):
    a = sim(R0, **kw); b = sim(Rw, **kw); c = sim(Rc, **kw)
    ws = [sim(Rw, start=s, **kw) for s in starts]
    print(f"{name:28s} normal {a[0]*100:+7,.0f}%/{a[1]*100:3.0f}% | weak {b[0]*100:+5,.0f}%/{b[1]*100:3.0f}% | cost$2 {c[0]*100:+6,.0f}%/{c[1]*100:3.0f}% | weak worst-start {min(w[0] for w in ws)*100:+4.0f}% maxDD {max(w[1] for w in ws)*100:3.0f}%")
row("dd*edge max5 (current)")
row("dd only max5", use_edge=False)
row("dd*edge max3", mx=3)
row("dd*edge*dtrend max5", dtr=True)
for n in (20, 50, 100):
    for lowv in (0.0, 0.5):
        row(f"dd*edge max5 eqEMA{n} low{lowv}", eqn=n, eqlow=lowv)
row("dd*edge max5 fullDD 10", full_dd=0.1)
row("dd*edge max5 fullDD 30", full_dd=0.3)
row("dd*edge max5 cap 10", cap=10)
row("dd*edge max5 cap 20", cap=20)
