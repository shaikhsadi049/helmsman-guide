"""Combine the 10 researchers' recommendations into one portfolio; compare with today's Assay.
Each slot: a menu of exits (legs may be blended 50/50). Two versions:
 FIXED  = the recommended exit used from day one (choice informed by 2025+ analysis -> optimistic)
 CAUSAL = each month, per slot, choose between today's exit and the recommendation by the past book's sumR/max(maxDD,1)
          on signals whose outcome was already known (warm-up 2024-06..12 included). Entry filters are causal too."""
import sys; sys.path.insert(0, "."); sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import lab
SIG = lab.SIG; F = lab.load_F(); R_ = lab.load_R(); X_ = lab.load_X(); LK_ = lab.load_LK()
pi = lambda **k: lab.policy_index(**k)[0]
T = lambda sq, tp, part, be, trail, rat, ts: pi(kind="trend", sq=sq, tp=tp, part=part, be=be, trail=trail, rat=rat, ts=ts)
Fd = lambda sq, tp, be, rat, hm: pi(kind="fade", sq=sq, tp=tp, be=be, rat=rat, hm=hm)
REC = {  # slot: (list of legs [policy idx], weight)
 "S1": ([T("k70","none","slot","none","h4q80","none","none"), T("k70","none","none","be1","h4q80","none","none")], 1.0),
 "S2": ([T("k50","3R","none","be1","h4q80","q90k50","ts_half"), T("k50","3R","none","be1","h4q80","q70k50","ts_half")], 1.0),
 "S3": ([T("k70","3R","slot","none","h4q50","none","none")], 1.0),
 "S4": ([T("k70","none","none","none","atr4","none","none")], 1.0),
 "S5": ([lab.baseline_policy("S5")], 1.0),
 "S6": ([T("k70","3R","none","be1","h4q80","none","none")], 0.5),     # S6 is a subset of S3 -> half weight
 "S7": ([T("k50","none","none","none","h4q80","q90k50","none")], 0.5),
 "F8": ([Fd("k50","f50","none","none",1.0)], 1.0),
 "F9": ([Fd("k70","f70","be1","none",2.0)], 1.0),
 "F10": ([Fd("k70","mean","none","none",1.0)], 1.0),
 "F11": ([lab.baseline_policy("F11")], 0.5)}
BASE = {s: ([lab.baseline_policy(s)], 1.0) for s in REC}
BASE["S7"] = ([lab.baseline_policy("S7")], 0.0)                       # S7 is OFF in Assay today
MS = lab._ms(); M1 = SIG.m1.values
def legs_RX(rows, legs):
    R = np.mean([np.asarray(R_[rows, j]) for j in legs], axis=0)
    X = np.max([np.asarray(X_[rows, j]) for j in legs], axis=0)
    lk = np.stack([np.asarray(LK_[rows, j]) for j in legs]); LKv = np.where((lk < 0).any(0), 10**12, lk.max(0))
    return R, X, LKv
def skip_mask(slot, rows):
    """causal entry filters recommended by the researchers"""
    keep = np.ones(len(rows), bool)
    if slot == "S4":   # skip when the H4 stack disagrees, while past such signals lost on average
        bad = F.h4_stack.values[rows] != 1; base = lab.baseline_policy("S4"); Xb = np.asarray(X_[rows, base]); Rb = np.asarray(R_[rows, base])
        for i in np.where(bad)[0]:
            past = bad & (Xb < M1[rows[i]])
            if past.sum() >= 5 and Rb[past].mean() < 0: keep[i] = False
    if slot == "S7":   # skip when H1 ADX above the 80th pct of earlier S7 signals
        adx = F.h1_adx.values[rows]
        for i in range(len(rows)):
            if i >= 50 and adx[i] > np.quantile(adx[:i], 0.8): keep[i] = False
    return keep
def book_score(R, X, m, upto):
    """one-at-a-time book on signals fully known before `upto`: sumR / max(maxDD, 1)"""
    ok = X < upto; R = R[ok]; X = X[ok]; m = m[ok]
    take = np.zeros(len(R), bool); free = -1
    for k in range(len(R)):
        if m[k] > free: take[k] = True; free = X[k]
    r = R[take]
    if len(r) < 10: return -np.inf
    eq = np.cumsum(r); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    return eq[-1] / max(dd, 1.0)
def slot_stream(slot, mode):
    rows = np.where(SIG.slot.values == slot)[0]
    legsB, _ = BASE[slot]; legsR, w = REC[slot]
    RB, XB, LB = legs_RX(rows, legsB); RR, XR, LR = legs_RX(rows, legsR)
    keep = skip_mask(slot, rows) if mode != "base" else np.ones(len(rows), bool)
    if mode == "base": R, X, L = RB, XB, LB; w = BASE[slot][1]
    elif mode == "fixed": R, X, L = RR, XR, LR
    else:  # causal monthly choice between today's exit and the recommendation
        R, X, L = RB.copy(), XB.copy(), LB.copy(); m = M1[rows]
        for a, b in zip(MS[:-1], MS[1:]):
            t = (m >= a) & (m < b)
            if not t.any(): continue
            sB = book_score(RB[keep], XB[keep], m[keep], a); sR = book_score(RR[keep], XR[keep], m[keep], a)
            if sR > sB: R[t], X[t], L[t] = RR[t], XR[t], LR[t]
    sel = keep & (lab.TIME[rows] >= lab.D0)
    rr = rows[sel]; R, X, L = R[sel], X[sel], L[sel]
    take = lab.greedy(rr, X)
    return pd.DataFrame(dict(slot=slot, t_in=M1[rr[take]] + 1, t_out=X[take], t_lock=L[take], R=R[take], w=w,
                             time=lab.TIME[rr[take]], kind=SIG.kind.values[rr[take]], risk=SIG.atr.values[rr[take]]))
def portfolio(mode):
    return pd.concat([slot_stream(s, mode) for s in REC], ignore_index=True).sort_values("t_in").reset_index(drop=True)
# ------- portfolio money simulation: dynamic risk 1..Max (trend x drawdown; fades inverse, x0.5), open-risk cap 15%
DTall = pd.read_parquet("../trades_v3_reg.parquet") if False else None
import mr as M
def money(P, R, mx=5, mn=1, fdd=0.2, cap=15):
    dt = M.dt_at(P.t_in.values - 1)
    ev = sorted([(a, 1, i) for i, a in enumerate(P.t_in.values)] + [(b, 0, i) for i, b in enumerate(P.t_out.values)])
    eq = peak = 1.0; mdd = 0; open_ = {}; curve = []
    for t, typ, i in ev:
        if typ == 0:
            if i in open_: eq += open_.pop(i) * R[i]; peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak); curve.append((i, eq))
            continue
        xdd = max(0.0, 1 - (1 - eq / peak) / fdd); fade = P.kind.values[i] == "fade"
        x = xdd * ((1 - dt[i]) if fade else dt[i])
        rp = (mn + (mx - mn) * x) * (0.5 if fade else 1.0) * P.w.values[i]
        room = eq * cap / 100 - sum(v for j, v in open_.items() if P.t_lock.values[j] > t)
        if room <= 0 or rp <= 0: continue
        open_[i] = min(eq * rp / 100, room)
    cv = pd.DataFrame(curve, columns=["i", "eq"]); cv["t"] = P.time.values[cv.i.values]
    return eq - 1, mdd, cv
def smooth(cv):
    s = pd.Series(cv["eq"].values, index=pd.DatetimeIndex(cv.t).tz_localize(None))
    d = s.groupby(s.index.floor("D")).last(); lr = np.log(d).diff().dropna()
    m = s.groupby(s.index.to_period("M")).last(); mr_ = m.pct_change().fillna(m.iloc[0] - 1)
    w = s.groupby(s.index.to_period("W")).last().pct_change().dropna()
    x = np.arange(len(d)); r2 = np.corrcoef(x, np.log(d.values))[0, 1] ** 2
    top5 = lr.nlargest(5).sum() / np.log(d.iloc[-1]) * 100
    return dict(months_pos=f"{(mr_>0).sum()}/{len(mr_)}", weeks_pos=f"{(w>0).mean()*100:.0f}%", logeq_R2=round(r2, 3), top5days=f"{top5:.0f}%",
                worst_month=f"{mr_.min()*100:+.1f}%", median_month=f"{mr_.median()*100:+.1f}%")
if __name__ == "__main__":
    out = {}
    for mode in ("base", "fixed", "causal"):
        P = portfolio(mode); P.to_parquet(f"port_{mode}.parquet"); out[mode] = P
        Rr = P.R.values * 1.0; Rw = np.where(Rr > 0, Rr * .5, Rr)
        mR = lab.metrics(Rr * P.w.values, P.time)
        print(f"\n=== {mode.upper()}: R-level (weights applied) n {mR['n']} PF {mR['PF']} sumR {mR['sumR']} maxDD {mR['maxDD_R']}R months+ {mR['months_pos']} "
              f"weeks+ {mR['weeks_pos_pct']}% eqR2 {mR['eq_R2']} top5days {mR['top5days_pct']}%")
        for mx in (2, 3, 5):
            a, dd, cv = money(P, Rr, mx); b, ddw, _ = money(P, Rw, mx)
            print(f"   risk 1..{mx}%: {a*100:+9,.0f}% maxDD {dd*100:4.1f}% | weak {b*100:+7,.0f}% DD {ddw*100:4.1f}% | {smooth(cv)}", flush=True)
    import pickle
    curves = {}
    for mode, P in out.items():
        for mx in (2, 5):
            curves[(mode, mx)] = money(P, P.R.values * 1.0, mx)[2]
    pickle.dump(curves, open("port_curves.pkl", "wb"))
