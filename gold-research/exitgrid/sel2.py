"""Causal regime-conditional exit choice, v2: exponential memory (half-life in months), risk-adjusted score, and 'deviation from normal'
features (z vs the exponentially weighted recent past of the same slot). usage: python sel2.py broker|comex"""
import sys, itertools, numpy as np, pandas as pd, warnings, pickle; warnings.filterwarnings("ignore")
DATA = sys.argv[1]; S = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad"
sys.path.insert(0, S + ("/dk/lab" if DATA == "broker" else "/lab")); import lab
R = np.nan_to_num(np.load(f"R_{DATA}.npy").astype(np.float64)); X = np.load(f"X_{DATA}.npy"); rows = np.load(f"rows_{DATA}.npy"); CB = pd.read_csv("combos.csv")
SIG = lab.SIG.iloc[rows].reset_index(drop=True); F = lab.load_F().iloc[rows].reset_index(drop=True); TIME = pd.DatetimeIndex(SIG.time)
Rc = np.clip(R, -1.5, 8.0); K = R.shape[1]; SLOTS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
BASE = {"volH1": "h1_atr_rank", "volH4": "h4_atr_rank", "volD1": "d1_atr_rank", "adxH1": "h1_adx", "adxH4": "h4_adx", "adxD1": "d1_adx",
        "effH1": "h1_er30", "effH4": "h4_er30", "stackH4": "h4_stack", "ribbonD1": "d1_ribbon", "dayrange": "day_rng_atr", "hour": "hour",
        "posH4": "h4_rngpos20", "distD1": "d1_dist20", "volume": "vol60_vs_day", "squeezeH1": "h1_bbw_rank"}
BASE = {k: v for k, v in BASE.items() if v in F.columns}
def rank_bucket(x, ii):
    b = np.full(len(x), -1)
    for k, i in enumerate(ii):
        p = x[ii[:k]]; p = p[np.isfinite(p)]
        if len(p) >= 50 and np.isfinite(x[i]): r = (p < x[i]).mean(); b[i] = 0 if r < 1/3 else (1 if r < 2/3 else 2)
    return b
def dev_bucket(x, ii, hl=100):
    """how far from the slot's recent normal and in which direction: z vs EWM mean/std of PAST signals; <-1 low, |z|<=1 normal, >1 high"""
    s = pd.Series(x[ii]); mu = s.ewm(halflife=hl, min_periods=50).mean().shift(1); sd = s.ewm(halflife=hl, min_periods=50).std().shift(1)
    z = ((s - mu) / sd).values; b = np.full(len(x), -1); ok = np.isfinite(z)
    b[ii[ok]] = np.where(z[ok] < -1, 0, np.where(z[ok] > 1, 2, 1)); return b
B = {}
for name, col in BASE.items():
    x = F[col].values.astype(float); br = np.full(len(SIG), -1); bd = np.full(len(SIG), -1)
    for slot in SLOTS:
        ii = np.where(SIG.slot.values == slot)[0]; br[ii] = rank_bucket(x, ii)[ii]
        if col not in ("hour", "h4_stack"): bd[ii] = dev_bucket(x, ii)[ii]
    B["rank:" + name] = br
    if col not in ("hour", "h4_stack"): B["dev:" + name] = bd
names = list(B); SPLITS = [("none", None)] + [(n, (n,)) for n in names] + [(f"{a} × {b}", (a, b)) for a, b in itertools.combinations(names, 2)]
def bucket_of(split):
    if split is None: return np.zeros(len(SIG), int)
    if len(split) == 1: b = B[split[0]]; return np.where(b < 0, 9, b)
    a, c = B[split[0]], B[split[1]]; return np.where((a < 0) | (c < 0), 9, a * 3 + c)
D0, TEND = lab.D0, pd.Timestamp("2026-08-01", tz="UTC"); LAM = 30.0
months = pd.period_range("2025-01", "2026-07", freq="M")
mst = {m: SIG.m1.values[min(np.searchsorted(TIME.values, m.to_timestamp().tz_localize("UTC").to_datetime64()), len(SIG) - 1)] for m in months}
xmax = X.max(1)
# resolve month of each signal (first month whose start is after its last exit)
SL = {slot: np.where(SIG.slot.values == slot)[0] for slot in SLOTS}
def select(bk, hl, score):
    ch = np.full(len(SIG), -1); dec = 0.5 ** (1.0 / hl) if hl else 1.0
    for slot, ii in SL.items():
        S1 = np.zeros((10, K)); S2 = np.zeros((10, K)); W = np.zeros(10); added = np.zeros(len(ii), bool)
        for m in months:
            S1 *= dec; S2 *= dec; W *= dec
            new = (~added) & (xmax[ii] < mst[m])
            if new.any():
                jj = ii[new]; np.add.at(S1, bk[jj], Rc[jj]); np.add.at(S2, bk[jj], Rc[jj] ** 2); np.add.at(W, bk[jj], 1.0); added |= new
            Wg = W.sum()
            if added.sum() < 30: continue
            gm = S1.sum(0) / Wg; gv = np.maximum(S2.sum(0) / Wg - gm ** 2, 1e-6)
            lo, hi = m.to_timestamp().tz_localize("UTC"), (m + 1).to_timestamp().tz_localize("UTC")
            cur = ii[(TIME[ii] >= lo) & (TIME[ii] < hi)]
            for b in np.unique(bk[cur]):
                if b == 9: mean, var = gm, gv
                else:
                    mean = (S1[b] + LAM * gm) / (W[b] + LAM); var = np.maximum((S2[b] + LAM * (gv + gm ** 2)) / (W[b] + LAM) - mean ** 2, 1e-6)
                sc = mean if score == "mean" else mean / np.sqrt(var)
                ch[cur[bk[cur] == b]] = int(np.argmax(sc))
    return ch
def evaluate(ch, w8={"S6": .5, "S7": .5}):
    parts = []
    for slot, ii0 in SL.items():
        ii = ii0[(TIME[ii0] >= D0) & (TIME[ii0] < TEND) & (ch[ii0] >= 0)]
        r = R[ii, ch[ii]]; x = X[ii, ch[ii]]; t = lab.greedy(rows[ii], x)
        parts.append(pd.DataFrame(dict(t=TIME[ii[t]], R=r[t] * w8.get(slot, 1.0), slot=slot)))
    d = pd.concat(parts).sort_values("t"); m = lab.metrics(d.R.values, pd.DatetimeIndex(d.t)); mo = d.groupby(d.t.dt.tz_localize(None).dt.to_period("M")).R.sum()
    return dict(sumR=round(m["sumR"], 1), DD=round(m["maxDD_R"], 1), calmar=round(m["sumR"] / max(m["maxDD_R"], 1e-6), 1), mpos=m["months_pos"],
                worst=round(mo.min(), 1), sh=round(mo.mean() / mo.std(), 2))
res = []
for fx in [("k70", "3R", 1.0, "none", 0.0, 0), ("k70", "3R", 1.0, "1.5R/0.5", 0.0, 0), ("k70", "q85", 1.0, "1.5R/0.5", 0.0, 0), ("k70", "none", 1.0, "1.5R/0.5", 1.5, 0)]:
    j = CB.index[(CB.sq == fx[0]) & (CB.tp == fx[1]) & (CB.be == fx[2]) & (CB.gb == fx[3]) & (CB.trail == fx[4]) & (CB.flip == fx[5])][0]
    res.append(dict(cfg="FIXED " + "/".join(map(str, fx)), hl=None, score=None, **evaluate(np.full(len(SIG), j))))
CH = {}
for hl in (0, 6, 3):
    for score in ("mean", "sharpe"):
        for sn, sp in SPLITS:
            ch = select(bucket_of(sp), hl, score); r = evaluate(ch); res.append(dict(cfg=sn, hl=hl or "all", score=score, **r))
            if sp is None or len(sp) == 1: CH[(sn, hl, score)] = ch
        print(DATA, "hl", hl, score, "done", flush=True)
T = pd.DataFrame(res); T.to_csv(f"sel2_{DATA}.csv", index=False); pickle.dump(CH, open(f"ch2_{DATA}.pkl", "wb"))
print("configs:", len(T), "| splits", len(SPLITS), "x 6 (memory x score) x 1080 combos x 7 slots x 19 months =", len(SPLITS) * 6 * 1080 * 7 * 19)
