import numpy as np, pandas as pd
T0 = pd.read_parquet("../trades_v3_reg.parquet")
def sim(T, R, mx=5, mn=1, full_dd=0.2, cap=15, start=0):
    SL = T.slot.values; TI = T.t_in.values; TO = T.t_out.values; TL = T.t_lock.values; ED = T.edge.values
    EV = sorted([(a, 1, i) for i, a in enumerate(TI)] + [(b, 0, i) for i, b in enumerate(TO)])
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set()
    for t, typ, i in EV:
        if TI[i] < start: continue
        if typ == 0:
            if i in open_: eq += open_.pop(i) * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
            continue
        if SL[i] in busy: continue
        x = max(0.0, 1 - (1 - eq / peak) / full_dd) * (0.5 + 0.5 * np.clip((ED[i] - 0.73) / 1.87, 0, 1))
        amt = eq * (mn + (mx - mn) * x) / 100
        room = eq * cap / 100 - sum(v for j, v in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(amt, room); busy.add(SL[i])
    return eq - 1, mdd
def row(name, T, mx):
    R0 = T.R.values; Rw = np.where(R0 > 0, R0 * .5, R0); Rc = R0 - 1.66 / T.risk.values
    st = T.t_in.values[np.searchsorted(T.time.values, np.datetime64("2026-02-01"))]
    a, b, c, d = sim(T, R0, mx), sim(T, Rw, mx), sim(T, Rc, mx), sim(T, Rw, mx, start=st)
    print(f"{name:14s} max{mx} normal {a[0]*100:+7,.0f}%/{a[1]*100:3.0f}% | weak {b[0]*100:+5,.0f}%/{b[1]*100:3.0f}% | cost$2 {c[0]*100:+6,.0f}%/{c[1]*100:3.0f}% | weak from 2026-02 {d[0]*100:+4.0f}%/{d[1]*100:3.0f}%")
for mx in (3, 5):
    row("all 7", T0, mx)
    for s in range(7):
        row(f"without S{s+1}", T0[T0.slot != s].reset_index(drop=True), mx)
