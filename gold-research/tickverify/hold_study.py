"""(C) stop audit, (A) higher-TF trend flip while trade is in loss / small profit, (B) a far runner closes -> other same-direction weak trades.
On the finding-72 exits, every tick. usage: python hold_study.py broker|comex"""
import sys, numpy as np, pandas as pd, pickle, talib, warnings; warnings.filterwarnings("ignore")
src = open("tick_spec.py").read(); exec(src.split("SPEC = {")[0].replace("@njit(parallel=True)", "@njit"))
SRC = sys.argv[2] if len(sys.argv) > 2 else "new"; SIG = lab.SIG
if SRC == "new": NEW = pickle.load(open(f"tick_spec_{DATA}.pkl", "rb"))
else:
    NEW = {}
    for slot in ("S1", "S2", "S3", "S4", "S5", "S6"):
        sq = lab.P[lab.baseline_policy(slot)]["sq"]
        if DATA == "broker":
            OB = pickle.load(open(S + "/dk/of/broker_tick.pkl", "rb")); r = OB[slot]; R_, X_ = r["today"]; rows_ = r["rows"]
        else:
            R_, X_, kk, rows_ = np.load(f"{S}/of/tk_{slot}_today.npy"); rows_ = rows_.astype(int); X_ = X_.astype(int)
        NEW[slot] = dict(rows=rows_, R=R_, X=X_.astype(int), risk=np.clip(SIG[sq].values[rows_], 0.5, 8.0) * SIG.atr.values[rows_])
m1ns = idx.values.astype("datetime64[ns]").astype(np.int64)
W = {"S6": .5, "S7": .5} if (len(sys.argv) < 3 or sys.argv[2] == "new") else {}
def htf(rule):
    b = m1.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    if rule == "1D": b = b[b.index.dayofweek < 5]
    ct = (b.index + pd.Timedelta(rule)).values.astype("datetime64[ns]").astype(np.int64); c = b.close.values
    e20, e50 = talib.EMA(c, 20), talib.EMA(c, 50)
    return {"x": (ct, e20 < e50, e20 > e50), "c50": (ct, c < e50, c > e50)}
HT = {"H4": htf("4h"), "D1": htf("1D")}
# trades actually taken by each strategy (one at a time)
T = []
for slot, r in NEW.items():
    ok = np.isfinite(r["R"]); rr = r["rows"][ok]; t = lab.greedy(rr, r["X"][ok])
    for k in np.where(ok)[0][t]:
        row = r["rows"][k]; tin = m1ns[SIG.m1.values[row]] + 60 * 10**9; tout = m1ns[min(r["X"][k], len(m1ns) - 1)] + 60 * 10**9
        T.append(dict(slot=slot, row=row, tin=tin, tout=tout, d=int(SIG.dir.values[row]), risk=r["risk"][k], R=r["R"][k], w=W.get(slot, 1.0)))
T = pd.DataFrame(T).sort_values("tin").reset_index(drop=True); n = len(T)
s0 = np.searchsorted(ts, T.tin.values); s1 = np.searchsorted(ts, T.tout.values)
ENTRY = np.where(T.d.values == 1, ASK[np.minimum(s0, len(ts) - 1)], BID[np.minimum(s0, len(ts) - 1)])
def path(i):
    d = T.d.values[i]; p = BID[s0[i]:s1[i]] if d == 1 else ASK[s0[i]:s1[i]]; return ((p - ENTRY[i]) * d - COST) / T.risk.values[i], ts[s0[i]:s1[i]]
PEAK = np.zeros(n); MAE = np.zeros(n)
for i in range(n):
    r, _ = path(i)
    if len(r): PEAK[i] = r.max(); MAE[i] = r.min()
fin = T.R.values
# runner events: a trade that had run >= 3R and closed giving some back (final < 0.8 x peak)  -> its close time
RUN = np.where((PEAK >= 3) & (fin < 0.8 * PEAK) & (fin >= 1))[0]
rules_A = [(tf, kind, th) for tf in ("H4", "D1") for kind in ("x", "c50") for th in (0.0, 0.5, 1.0, 99.0)]
rules_B = [0.0, 0.5, 1.0]
NA = {k: fin.copy() for k in rules_A}; NB = {k: fin.copy() for k in rules_B}; NB_all = {k: fin.copy() for k in rules_B}
for i in range(n):
    r, tt = path(i)
    if len(r) < 2: continue
    d = T.d.values[i]
    for (tf, kind, th) in rules_A:
        ct, lb, sb = HT[tf][kind]; bad = lb if d == 1 else sb
        j0, j1 = np.searchsorted(ct, T.tin.values[i], side="right"), np.searchsorted(ct, T.tout.values[i], side="left")
        for k in np.where(bad[j0:j1])[0]:
            q = np.searchsorted(tt, ct[j0 + k])
            if q < len(r) and r[q] < th: NA[(tf, kind, th)][i] = r[q]; break
    ev = RUN[(T.d.values[RUN] == d) & (T.slot.values[RUN] != T.slot.values[i]) & (T.tout.values[RUN] > T.tin.values[i]) & (T.tout.values[RUN] < T.tout.values[i])]
    for th in rules_B:
        for e in sorted(T.tout.values[ev]):
            q = np.searchsorted(tt, e)
            if q < len(r) and r[q] < th: NB[th][i] = r[q]; break
TEND = pd.Timestamp("2026-08-01", tz="UTC"); E0, E1 = pd.Timestamp("2026-01-26", tz="UTC"), pd.Timestamp("2026-02-04", tz="UTC")
TT = pd.to_datetime(T.tin.values, utc=True); LIVE = (TT >= lab.D0) & (TT < TEND) & ~((TT >= E0) & (TT < E1))
def rep(Rv, mask=None):
    m = LIVE if mask is None else (LIVE & mask)
    d = pd.DataFrame(dict(t=TT[m], R=Rv[m] * T.w.values[m])).sort_values("t"); mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
    eq = d.R.cumsum().values; dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    return dict(R=round(eq[-1], 1), DD=round(dd, 1), mpos=f"{(mo > 0).sum()}/{len(mo)}", worst=round(mo.min(), 1), sh=round(mo.mean() / mo.std(), 2))
print(f"\n### {DATA}: (C) STOP AUDIT (finding-72 exits, trend trades, Jan move excluded)")
aud = []
for slot in sorted(T.slot.unique()):
    m = LIVE & (T.slot.values == slot); los = m & (fin < 0); win = m & (fin >= 1)
    aud.append(dict(slot=slot, trades=int(m.sum()), losers=int(los.sum()), full_stop_pct=round((fin[los] <= -0.9).mean() * 100),
                    avg_loss=round(fin[los].mean(), 2), winners_1R=int(win.sum()),
                    win_MAE_gt_0_5R_pct=round((MAE[win] < -0.5).mean() * 100), win_MAE_gt_0_7R_pct=round((MAE[win] < -0.7).mean() * 100),
                    losers_never_up_0_3R_pct=round((PEAK[los] < 0.3).mean() * 100), stop_usd_median=round(np.median(T.risk.values[m]), 1)))
print(pd.DataFrame(aud).to_string(index=False))
print(f"\n### {DATA}: (A) higher-TF trend flips against the trade while open profit < th -> exit")
rows = [dict(rule="hold (finding-72 exits)", **rep(fin))]
for k, v in NA.items(): rows.append(dict(rule=f"{k[0]} {'EMA20xEMA50' if k[1]=='x' else 'close vs EMA50'} flip & open<{'any' if k[2]==99 else str(k[2])+'R'}", **rep(v)))
A_ = pd.DataFrame(rows); print(A_.to_string(index=False))
print(f"\n### {DATA}: (B) a runner (peak>=3R, closed giving back) closes -> other same-direction trades with open profit < th close too  | runner events: {len(RUN)}")
rows = [dict(rule="hold", **rep(fin))] + [dict(rule=f"close others with open < {th}R", **rep(v)) for th, v in NB.items()]
B_ = pd.DataFrame(rows); print(B_.to_string(index=False))
# per strategy for the best A and B rules
bestA = max(NA, key=lambda k: rep(NA[k])["sh"]); print("\nper strategy, best A rule", bestA)
print(pd.DataFrame([dict(slot=s, hold=rep(fin, T.slot.values == s)["R"], hold_sh=rep(fin, T.slot.values == s)["sh"],
      A=rep(NA[bestA], T.slot.values == s)["R"], A_sh=rep(NA[bestA], T.slot.values == s)["sh"],
      B05=rep(NB[0.5], T.slot.values == s)["R"], B05_sh=rep(NB[0.5], T.slot.values == s)["sh"]) for s in sorted(T.slot.unique())]).to_string(index=False))
print("trades whose exit the A-rule changed:", {f"{k[0]}-{k[1]}-{k[2]}": int((NA[k][LIVE] != fin[LIVE]).sum()) for k in NA if k[2] in (0.0, 99.0)}, "of", int(LIVE.sum()))
print("trades whose exit the B-rule changed:", {th: int((NB[th][LIVE] != fin[LIVE]).sum()) for th in NB})
pickle.dump(dict(T=T, PEAK=PEAK, MAE=MAE, NA=NA, NB=NB), open(f"hold_{DATA}_{SRC}.pkl", "wb"))
