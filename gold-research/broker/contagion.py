"""When one trend strategy is stopped out, act on the OTHER open same-direction trend trades (and/or pause new ones). Broker bid/ask ticks, causal."""
import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../..")
import numpy as np, pandas as pd, pickle, glob, warnings; warnings.filterwarnings("ignore")
import lab, prules as PR
SIG = lab.SIG; M1 = SIG.m1.values; OUT = pickle.load(open("broker_tick.pkl", "rb")); POL = lab.P
idx = pd.DatetimeIndex(pd.read_parquet("../m1_bid.parquet", columns=["close"]).index)
fs = sorted(glob.glob("../hdt/*.parquet"), key=lambda f: tuple(int(x) for x in f.split("/")[-1][:-8].split("_")))
tk = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
ts = tk.time.values.astype("datetime64[ns]").astype(np.int64); o = np.argsort(ts, kind="stable"); ts = ts[o]
BID = tk.bid.values[o].astype(np.float64); ASK = tk.ask.values[o].astype(np.float64); del tk
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
REC7 = lab.policy_index(kind="trend", sq="k50", tp="none", part="none", be="none", trail="h4q80", rat="q90k50", ts="none")[0]
LEGS = [("S1","today",1,False),("S2","A3",1,True),("S3","A3",1,False),("S4","B",1,True),("S5","today",1,True),("S6","A3",.5,False),("S7","rec",.5,True)]
FADE = [("F8","rec",1),("F9","rec",1),("F10","rec",1),("F11","today",.5)]
def sq_of(slot, spec):
    if spec == "today": return POL[lab.baseline_policy(slot)]["sq"]
    if spec == "rec": return POL[REC7]["sq"]
    return SQ[slot]
rows = []
for slot, spec, w, adx in LEGS:
    r = OUT[slot]; rr0 = r["rows"]; R, X = r[spec]; ok = np.isfinite(R); rr = rr0[ok]; t = lab.greedy(rr, X[ok])
    ww = w * (np.where(r["adx_bad"][ok][t], 0.5, 1.0) if adx else np.ones(t.sum()))
    rs = rr[t]; k = np.clip(SIG[sq_of(slot, spec)].values[rs], 0.5, 8.0); risk = k * SIG.atr.values[rs]
    tin = (idx[M1[rs]] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64)
    i0 = np.searchsorted(ts, tin, side="left"); d = SIG.dir.values[rs]
    entry = np.where(d == 1, ASK[np.minimum(i0, len(ts) - 1)], BID[np.minimum(i0, len(ts) - 1)])
    txn = (idx[np.clip(X[ok][t], 0, len(idx) - 1)] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64)
    rows.append(pd.DataFrame(dict(slot=slot, t=tin, tx=txn, dir=d, R=R[ok][t], w=ww, entry=entry, risk=risk)))
T = pd.concat(rows, ignore_index=True).sort_values("t").reset_index(drop=True)
FR = []
for slot, spec, w in FADE:
    r = OUT[slot]; rr0 = r["rows"]; R, X = r[spec]; ok = np.isfinite(R); rr = rr0[ok]; t = lab.greedy(rr, X[ok])
    FR.append(pd.DataFrame(dict(t=lab.TIME[rr[t]], R=R[ok][t] * w, slot=slot)))
FR = pd.concat(FR, ignore_index=True)
def px_at(tau, d):  # exit price at time tau for direction d
    j = min(np.searchsorted(ts, tau, side="left"), len(ts) - 1); return BID[j] if d == 1 else ASK[j]
def be_hit(tau, tx, d, entry):  # does price come back to entry between tau and original exit?
    a, b = np.searchsorted(ts, tau), np.searchsorted(ts, tx)
    if b <= a: return False
    p = BID[a:b] if d == 1 else ASK[a:b]
    return bool((p <= entry).any()) if d == 1 else bool((p >= entry).any())
def run(action, trig_R=-0.8, cool_h=0, same_dir=True):
    newR = T.R.values.copy(); w = T.w.values.copy(); t = T.t.values; tx = T.tx.values; d = T.dir.values; sl = T.slot.values
    trig = np.where(T.R.values <= trig_R)[0]                       # original stop-outs (known at their exit time)
    acted = np.zeros(len(T), bool)
    for g in trig:
        tau = tx[g]
        others = np.where((t < tau) & (tx > tau) & (sl != sl[g]) & ((d == d[g]) if same_dir else True) & ~acted)[0]
        for i in others:
            open_R = ((px_at(tau, d[i]) - T.entry.values[i]) * d[i] - 0.07) / T.risk.values[i]
            if action == "close_losers" and open_R < 0: newR[i] = open_R; acted[i] = True
            elif action == "close_all": newR[i] = open_R; acted[i] = True
            elif action == "half_all": newR[i] = 0.5 * open_R + 0.5 * newR[i]; acted[i] = True
            elif action == "be_winners" and open_R > 0:
                if be_hit(tau, tx[i], d[i], T.entry.values[i]): newR[i] = -0.07 / T.risk.values[i]
                acted[i] = True
            elif action == "close_losers_be_winners":
                if open_R < 0: newR[i] = open_R
                elif be_hit(tau, tx[i], d[i], T.entry.values[i]): newR[i] = -0.07 / T.risk.values[i]
                acted[i] = True
        if cool_h:
            blk = np.where((t > tau) & (t <= tau + cool_h * 3600 * 10**9) & (sl != sl[g]) & ((d == d[g]) if same_dir else True))[0]
            w[blk] = 0.0
    out = pd.DataFrame(dict(t=pd.to_datetime(t, utc=True), R=newR * w, slot=sl))
    z = pd.concat([out, FR], ignore_index=True); z["t"] = pd.to_datetime(z.t, utc=True); return z
D0, TEND = lab.D0, pd.Timestamp("2026-08-01", tz="UTC")
res = []
for name, kw in [("base", dict(action="none")), ("close_losers", dict(action="close_losers")), ("close_all", dict(action="close_all")),
                 ("half_all", dict(action="half_all")), ("be_winners", dict(action="be_winners")), ("close_losers+be_winners", dict(action="close_losers_be_winners")),
                 ("pause 4h", dict(action="none", cool_h=4)), ("pause 12h", dict(action="none", cool_h=12)), ("pause 24h", dict(action="none", cool_h=24)),
                 ("be_winners+pause 12h", dict(action="be_winners", cool_h=12)), ("close_losers trig-0.5", dict(action="close_losers", trig_R=-0.5))]:
    r = PR.rep(run(**kw), lab, D0, TEND); r["calmar"] = round(r["sumR"] / r["DD"], 1); res.append(dict(rule=name, **r)); print(res[-1], flush=True)
pd.DataFrame(res).to_csv("contagion_broker.csv", index=False)
T.to_parquet("contagion_trades.parquet")
