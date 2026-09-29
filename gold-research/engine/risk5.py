"""Event-driven equity sim for EA v3 (7 slots, EA-style calcs) with per-trade risk %, open-risk cap and drawdown stop."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import v3_parity as V, dyn2_run as R2, adv3 as D, adv4, adv as A, gcdata as G_
idx = R2.idx
rows = []
for si, sl in enumerate(V.SLOTS):
    tf, fam, nc, sess, qsl, qtp, lock, qtr, f1 = sl
    E = V.entries_ea(tf, fam, nc, sess); G = R2.GR[tf]; m = E["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, qsl, 2.0), 0.5, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, qtp, 1.0) / k, 0.1, 3.0); tw = R2.trail_q(m, qtr) * E["atr4"]
    res = adv4.sim_dyn2(m, E["dir"].astype(np.int64), E["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c, R2.G4.mgmt, R2.G4.trend_up, R2.G4.trend_dn,
                        f1 if f1 > 0 else 1e-9, lock, False, G_.COST_RT, 60 * 24 * 30)
    sel = np.where(idx[m] >= R2.S25)[0]
    for j in sel:
        rows.append((si, int(m[j]) + 1, int(res[j, 2]), int(res[j, 4]) if res[j, 4] >= 0 else 10**12, res[j, 0]))
T = pd.DataFrame(rows, columns=["slot", "t_in", "t_out", "t_lock", "R"]).sort_values("t_in").reset_index(drop=True)
def simulate(rp, cap, ddstop, R=None, order=None):
    Rv = T.R.values if R is None else R
    ev = []  # (time, type, i)
    for i, (a, b) in enumerate(zip(T.t_in.values, T.t_out.values)): ev += [(a, 1, i), (b, 0, i)]
    ev.sort()
    eq = 1.0; peak = 1.0; mdd = 0; open_ = {}; busy = set(); taken = 0
    for t, typ, i in ev:
        if typ == 0:
            if i in open_: eq += open_.pop(i) * Rv[i]; peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
            continue
        s = T.slot.values[i]
        if s in busy and any(T.slot.values[j] == s for j in open_): continue
        if ddstop and eq < peak * (1 - ddstop): continue
        unlocked = sum(amt for j, amt in open_.items() if T.t_lock.values[j] > t)   # $ at risk (1R) of positions not yet risk-free
        amt = eq * rp / 100
        if cap:
            room = eq * cap / 100 - unlocked
            if room <= 0: continue
            amt = min(amt, room)
        open_[i] = amt; taken += 1
        busy = {T.slot.values[j] for j in open_}
    return eq - 1, mdd, taken
print("per-trade risk | caps                       | 19-month result | max drawdown | trades taken")
for rp, cap, dds in ((1, 0, 0), (2, 0, 0), (5, 0, 0), (5, 15, 0), (5, 15, 0.35), (5, 10, 0.35), (3, 12, 0.35)):
    r, dd, n = simulate(rp, cap, dds)
    print(f"{rp}%            | open-risk cap {cap or '-':>3}%, DD stop {int(dds*100) or '-':>3}% | {r*100:+14,.0f}% | {dd*100:5.1f}%       | {n}")
# weak market: winners halved
Rw = np.where(T.R.values > 0, T.R.values * 0.5, T.R.values)
print("\nWEAK MARKET (every winner halved):")
for rp, cap, dds in ((1, 0, 0), (5, 0, 0), (5, 15, 0.35), (5, 10, 0.35), (3, 12, 0.35)):
    r, dd, n = simulate(rp, cap, dds, R=Rw)
    print(f"{rp}% cap {cap or '-'}% DDstop {int(dds*100) or '-'}% -> {r*100:+,.0f}%  maxDD {dd*100:.1f}%  trades {n}")

def simulate_throttle(rp, cap, full_dd, floor, R=None):
    """risk = rp * max(floor, 1 - DD/full_dd): shrinks as equity falls below its peak, recovers with it."""
    Rv = T.R.values if R is None else R
    ev = sorted([(a, 1, i) for i, a in enumerate(T.t_in.values)] + [(b, 0, i) for i, b in enumerate(T.t_out.values)])
    eq = peak = 1.0; mdd = 0; open_ = {}
    for t, typ, i in ev:
        if typ == 0:
            if i in open_: eq += open_.pop(i) * Rv[i]; peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
            continue
        if any(T.slot.values[j] == T.slot.values[i] for j in open_): continue
        dd = 1 - eq / peak
        amt = eq * rp / 100 * max(floor, 1 - dd / full_dd)
        if cap:
            room = eq * cap / 100 - sum(a for j, a in open_.items() if T.t_lock.values[j] > t)
            if room <= 0: continue
            amt = min(amt, room)
        open_[i] = amt
    return eq - 1, mdd
print("\nRISK THROTTLE (risk shrinks with drawdown, recovers automatically)")
for rp, cap, fdd, fl in ((5, 0, 0.3, 0.2), (5, 15, 0.3, 0.2), (5, 15, 0.2, 0.1), (5, 10, 0.2, 0.1), (3, 10, 0.2, 0.2), (2, 8, 0.2, 0.25)):
    a = simulate_throttle(rp, cap, fdd, fl); b = simulate_throttle(rp, cap, fdd, fl, R=Rw)
    print(f"{rp}% base, cap {cap or '-'}%, risk->floor {int(fl*100)}% at DD {int(fdd*100)}% | 2025-26: {a[0]*100:+,.0f}% maxDD {a[1]*100:.1f}% | WEAK: {b[0]*100:+,.0f}% maxDD {b[1]*100:.1f}%")
