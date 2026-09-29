"""Tear apart dynamic risk 1..Max (dd*edge). All on 2025-01..2026-07."""
import numpy as np, pandas as pd
T = pd.read_parquet("../trades_v3.parquet")
SL = T.slot.values; TI = T.t_in.values; TO = T.t_out.values; TL = T.t_lock.values
EV = sorted([(a, 1, i) for i, a in enumerate(TI)] + [(b, 0, i) for i, b in enumerate(TO)])
Q = pd.PeriodIndex(T.time.dt.tz_localize(None), freq="Q").astype(str).values

def sim(R, mode="dd*edge", mx=5.0, mn=1.0, full_dd=0.2, cap=15, edge=None, lo=0.73, hi=2.6, start=0, ev=EV, track=False):
    E = T.edge.values if edge is None else edge
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set(); curve = []
    for t, typ, i in ev:
        if TI[i] < start: continue
        if typ == 0:
            if i in open_:
                eq += open_.pop(i) * R[i]; busy.discard(SL[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
                if track: curve.append((i, eq))
            continue
        if SL[i] in busy: continue
        xdd = max(0.0, 1 - (1 - eq / peak) / full_dd) if full_dd else 1.0
        lo_, hi_ = (lo, hi) if not callable(lo) else lo(i)
        xe = np.clip((E[i] - lo_) / (hi_ - lo_), 0, 1)
        x = {"dd": xdd, "edge": xe, "dd*edge": xdd * (0.5 + 0.5 * xe), "fixed": 1.0}[mode]
        amt = eq * (mn + (mx - mn) * x) / 100
        room = eq * cap / 100 - sum(a for j, a in open_.items() if TL[j] > t)
        if room <= 0: continue
        open_[i] = min(amt, room); busy.add(SL[i])
    return (eq - 1, mdd, curve) if track else (eq - 1, mdd)

R0 = T.R.values
Rw = np.where(R0 > 0, R0 * 0.5, R0)                       # weak market: every win halved
Rc = R0 - (2.0 - 0.34) / T.risk.values                     # cost $2/oz instead of $0.34
def f(r): return f"{r[0]*100:+9,.0f}% / {r[1]*100:4.1f}%"

print("=== 1. LOOK-AHEAD: edge thresholds 0.73/2.6 came from the whole period. Use only past signals instead ===")
ed = T.edge.values
def past_pct(i):
    h = ed[:i]
    if len(h) < 200: return (0.73, 2.6)
    return (np.percentile(h, 20), np.percentile(h, 80))
cache = {}
def lo_fn(i):
    if i not in cache: cache[i] = past_pct(i)
    return cache[i]
for name, R in (("normal", R0), ("weak", Rw), ("cost$2", Rc)):
    print(f"{name:7s} fixed 0.73/2.6: {f(sim(R))} | past-only: {f(sim(R, lo=lo_fn))}")

print("\n=== 2. Does edge help at all? Compare with RANDOM edge (shuffled, 20 runs) ===")
rng = np.random.default_rng(1)
for name, R in (("normal", R0), ("weak", Rw)):
    real = sim(R); dd_only = sim(R, mode="dd")
    rs = np.array([sim(R, edge=rng.permutation(ed)) for _ in range(20)])
    print(f"{name:7s} real edge {f(real)} | dd only {f(dd_only)} | random edge median {np.median(rs[:,0])*100:+,.0f}% / {np.median(rs[:,1])*100:.1f}%, "
          f"real beats random in {np.mean(rs[:,0] < real[0])*100:.0f}% (result) {np.mean(rs[:,1] > real[1])*100:.0f}% (DD)")

print("\n=== 3. Start-date luck: start on each month, result & DD to end ===")
months = pd.date_range("2025-01-01", "2026-04-01", freq="MS", tz="UTC")
print("start    | max5 normal       | max5 weak         | max3 weak")
for mth in months:
    st = TI[np.searchsorted(T.time.values, np.datetime64(mth.tz_localize(None)))] if (T.time >= mth).any() else 10**18
    print(f"{mth:%Y-%m}  | {f(sim(R0, start=st))} | {f(sim(Rw, start=st))} | {f(sim(Rw, mx=3, start=st))}")

print("\n=== 4. Quarter by quarter (max5 dd*edge, normal) ===")
r, d, cv = sim(R0, track=True)
cv = pd.DataFrame(cv, columns=["i", "eq"]); import gcdata; import dyn2_run as R2
qo = pd.PeriodIndex(pd.DatetimeIndex(R2.idx[np.minimum(TO[cv.i.values], len(R2.idx)-1)]).tz_localize(None), freq="Q").astype(str); cv["q"] = qo
prev = 1.0
for q, g in cv.groupby("q", sort=True):
    e = g["eq"].values; pk = np.maximum.accumulate(np.r_[prev, e]); qdd = (1 - np.r_[prev, e] / pk).max()
    print(f"{q}: {(e[-1]/prev-1)*100:+7.1f}%  DD inside quarter {qdd*100:4.1f}%"); prev = e[-1]

print("\n=== 5. Block bootstrap: reshuffle whole weeks (500 paths, 19 months) ===")
wk = (T.time.dt.tz_localize(None).dt.to_period("W")).astype(str).values
weeks = np.unique(wk); W = {w: np.where(wk == w)[0] for w in weeks}
wkstart = {w: TI[W[w]].min() for w in weeks}
base0 = min(wkstart.values()); WLEN = int(np.median(np.diff(sorted(wkstart.values()))))
print('bars per week', WLEN)
def boot(R, mx, n=500):
    out = []
    for _ in range(n):
        seq = rng.choice(weeks, len(weeks)); ev = []; off = 0; RR = []; base = []
        # re-time: week b is placed at slot b (offset = b*10080 minutes)
        idxs = []; tin = []; tout = []; tl = []
        for b, w in enumerate(seq):
            ii = W[w]; sh = base0 + b * WLEN - wkstart[w]
            idxs += list(ii); tin += list(TI[ii] + sh); tout += list(TO[ii] + sh); tl += list(np.where(TL[ii] < 10**11, TL[ii] + sh, TL[ii]))
        idxs = np.array(idxs)
        global TI_, TO_
        out.append(sim_b(R[idxs], SL[idxs], np.array(tin), np.array(tout), np.array(tl), ed[idxs], mx))
    return np.array(out)
def sim_b(R, sl, ti, to, tl, E, mx, mn=1.0, full_dd=0.2, cap=15):
    ev = sorted([(a, 1, i) for i, a in enumerate(ti)] + [(b, 0, i) for i, b in enumerate(to)])
    eq = peak = 1.0; mdd = 0; open_ = {}; busy = set()
    for t, typ, i in ev:
        if typ == 0:
            if i in open_: eq += open_.pop(i) * R[i]; busy.discard(sl[i]); peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
            continue
        if sl[i] in busy: continue
        xdd = max(0.0, 1 - (1 - eq / peak) / full_dd); xe = np.clip((E[i] - 0.73) / (2.6 - 0.73), 0, 1)
        amt = eq * (mn + (mx - mn) * xdd * (0.5 + 0.5 * xe)) / 100
        room = eq * cap / 100 - sum(a for j, a in open_.items() if tl[j] > t)
        if room <= 0: continue
        open_[i] = min(amt, room); busy.add(sl[i])
    return eq - 1, mdd
for name, R in (("normal", R0), ("weak", Rw)):
    for mx in (3, 5):
        b = boot(R, mx, 300)
        print(f"{name:6s} max{mx}: result median {np.median(b[:,0])*100:+,.0f}%  worst5% {np.percentile(b[:,0],5)*100:+,.0f}%  loss-prob {np.mean(b[:,0]<0)*100:.0f}% | "
              f"DD median {np.median(b[:,1])*100:.0f}%  worst5% {np.percentile(b[:,1],95)*100:.0f}%  DD>40% {np.mean(b[:,1]>0.4)*100:.0f}%")
