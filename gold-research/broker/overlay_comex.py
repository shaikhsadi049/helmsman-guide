"""COMEX version of contagion + giveback + trend-flip overlays (trade prints, cost $0.34/oz)."""
import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../bt"); sys.path.insert(0, "..")
import numpy as np, pandas as pd, pickle, talib, warnings; warnings.filterwarnings("ignore")
import lab, gcdata as G_, ticks as TK, dyn2_run as R2, prules as PR
SIG = lab.SIG; M1 = SIG.m1.values; POL = lab.P; idx = R2.idx; TD = pickle.load(open("tick_dyn_x.pkl", "rb"))
tk = TK.load_ticks("2024-12-15"); ts = tk.ts_event.values.astype("datetime64[ns]").astype(np.int64)
m1ns = idx.values.astype("datetime64[ns]").astype(np.int64); mi = np.clip(np.searchsorted(m1ns, ts, side="right") - 1, 0, len(idx) - 1)
P = tk.price.values + G_.ADJ[mi]; del tk; BID = ASK = P; COST = G_.COST_RT; print("ticks", len(ts), flush=True)
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
def sq_today(s): return POL[lab.baseline_policy(s)]["sq"]
def build(slot, src, w, adx, sq):
    if src[0] == "tk":
        Rv, Xv, k, rows = np.load(f"tk_{slot}_{src[1]}.npy"); rows = rows.astype(int); Xv = Xv.astype(int)
        keep = (k > 0) if src[1] == "recommended" else np.ones(len(rows), bool); ok = keep & np.isfinite(Rv); rr = rows[ok]; t = lab.greedy(rr, Xv[ok])
        rs = rr[t]; R = Rv[ok][t]; tx = idx[np.clip(Xv[ok][t], 0, len(idx) - 1)]; ww = np.full(len(rs), w)
    else:
        d = TD[(slot, src[1])]; srows = np.where(SIG.slot.values == slot)[0]; mp = {pd.Timestamp(a).tz_localize(None) if pd.Timestamp(a).tz else pd.Timestamp(a): r for a, r in zip(lab.TIME[srows], srows)}
        rs = np.array([mp[pd.Timestamp(x).tz_localize(None) if pd.Timestamp(x).tz else pd.Timestamp(x)] for x in d.t]); R = d.R.values; tx = pd.DatetimeIndex(d.tx)
        ww = w * (d.w.values if adx else np.ones(len(rs)))
    risk = np.clip(SIG[sq].values[rs], 0.5, 8.0) * SIG.atr.values[rs]
    tin = (idx[M1[rs]] + pd.Timedelta(minutes=1)).values.astype("datetime64[ns]").astype(np.int64); i0 = np.searchsorted(ts, tin, side="left")
    txn = (pd.DatetimeIndex(tx).tz_convert("UTC") if pd.DatetimeIndex(tx).tz else pd.DatetimeIndex(tx).tz_localize("UTC")) + pd.Timedelta(minutes=1)
    return pd.DataFrame(dict(slot=slot, t=tin, tx=txn.values.astype("datetime64[ns]").astype(np.int64), dir=SIG.dir.values[rs], R=R, w=ww, entry=P[np.minimum(i0, len(P) - 1)], risk=risk))
LEGS = [("S1", ("tk","today"), 1, False, sq_today("S1")), ("S2", ("dyn","A3"), 1, True, "k50"), ("S3", ("dyn","A3"), 1, False, "k70"),
        ("S4", ("dyn","B"), 1, True, "k70"), ("S5", ("tk","today"), 1, False, sq_today("S5")), ("S6", ("dyn","A3"), .5, False, "k70"), ("S7", ("tk","recommended"), .5, False, "k50")]
T = pd.concat([build(*l) for l in LEGS], ignore_index=True).sort_values("t").reset_index(drop=True)
FR = []
for f, sp, w in (("F8","recommended",1),("F9","recommended",1),("F10","recommended",1),("F11","today",.5)):
    Rv, Xv, k, rows = np.load(f"tk_{f}_{sp}.npy"); rows = rows.astype(int); Xv = Xv.astype(int)
    keep = (k > 0) if sp == "recommended" else np.ones(len(rows), bool); ok = keep & np.isfinite(Rv); rr = rows[ok]; t = lab.greedy(rr, Xv[ok])
    FR.append(pd.DataFrame(dict(t=lab.TIME[rr[t]], R=Rv[ok][t] * w, slot=f)))
FR = pd.concat(FR, ignore_index=True)
# reuse the broker overlay/contagion code paths
CS = open("../dk/of/contagion.py").read(); OS = open("../dk/of/overlay.py").read()
exec(CS[CS.index("def px_at"):CS.index("D0, TEND = lab.D0")])
m1 = R2.m1.copy(); m1["close"] = m1.close + G_.ADJ
exec(OS[OS.index("def bars(rule)"):OS.index("D0, TEND = lab.D0")].replace("COST = 0.07", "COST = G_.COST_RT"))
exec(CS[CS.index("def px_at"):CS.index("def run(")])
src_run = CS[CS.index("def run("):CS.index("D0, TEND = lab.D0")].replace("- 0.07)", "- COST)").replace("-0.07 /", "-COST /")
exec(src_run)
D0, TEND = lab.D0, pd.Timestamp("2026-08-01", tz="UTC"); res = []
def add(name, z):
    r = PR.rep(z, lab, D0, TEND); r["calmar"] = round(r["sumR"] / r["DD"], 1); res.append(dict(rule=name, **r)); print(res[-1], flush=True)
add("base", overlay("none")[0])
for nm, kw in [("close_losers", dict(action="close_losers")), ("close_losers trig-0.5", dict(action="close_losers", trig_R=-0.5)),
               ("half_all", dict(action="half_all")), ("be_winners", dict(action="be_winners")), ("close_all", dict(action="close_all"))]:
    add(nm, run(**kw))
for a in (1.0, 1.5, 2.0, 3.0):
    for b in (0.4, 0.5, 0.6, 0.7): add(f"giveback peak>={a}R keep {b}", overlay("giveback", a, b)[0])
for n in TR: add(f"trend flip: {n}", overlay("trend", n)[0]); add(f"trend flip (in profit): {n}", overlay("trend_if_profit", n)[0])
pd.DataFrame(res).to_csv("overlay_comex.csv", index=False)
