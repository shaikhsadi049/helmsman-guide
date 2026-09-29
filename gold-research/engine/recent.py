import numpy as np, pandas as pd
exec(open("dropslot.py").read().split("def row")[0])
T = T0[T0.slot != 6].reset_index(drop=True)
def simf(T, R, rp, cap=15, start=0):
    SL = T.slot.values; TI = T.t_in.values; TO = T.t_out.values; TL = T.t_lock.values
    EV = sorted([(a, 1, i) for i, a in enumerate(TI)] + [(b, 0, i) for i, b in enumerate(TO)])
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set(); sumR = 0
    for t, typ, i in EV:
        if TI[i] < start: continue
        if typ == 0:
            if i in open_: f = open_.pop(i); eq += f * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak); sumR += R[i] * (f > 0)
            continue
        if SL[i] in busy: continue
        room = eq * cap / 100 - sum(v for j, v in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(eq * rp / 100, room); busy.add(SL[i])
    return eq - 1, mdd, sumR
R0 = T.R.values; Rw = np.where(R0 > 0, R0 * .5, R0)
for st_s in ("2025-01-01", "2026-02-01", "2026-04-01"):
    st = T.t_in.values[np.searchsorted(T.time.values, np.datetime64(st_s))]
    print(f"from {st_s}:")
    for rp in (1, 2, 3, 5):
        a = simf(T, R0, rp, start=st); b = simf(T, Rw, rp, start=st)
        print(f"   fixed {rp}%: normal {a[0]*100:+8,.0f}%/{a[1]*100:3.0f}% (taken sumR {a[2]:+.0f}) | weak {b[0]*100:+6,.0f}%/{b[1]*100:3.0f}%")
    for mx in (3, 5):
        a = sim(T, R0, mx, start=st); b = sim(T, Rw, mx, start=st)
        print(f"   dyn 1-{mx}%: normal {a[0]*100:+8,.0f}%/{a[1]*100:3.0f}% | weak {b[0]*100:+6,.0f}%/{b[1]*100:3.0f}%")
