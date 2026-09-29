"""New signal families (RSI-2 dip, 20-bar breakout, EMA pullback) on 3m..1h, all with market-measured stops/targets/trails.
Judged on 2025-01..2026-07 by quarter."""
import itertools, time, numpy as np, pandas as pd, warnings
from multiprocessing import Pool
warnings.filterwarnings("ignore")
import adv_run as AR, adv3 as D, adv4, adv as A, gcdata as G_, engine as E, strat as S
m1 = AR.m1; idx = m1.index
S25 = pd.Timestamp("2025-01-01", tz="UTC"); H0 = pd.Timestamp("2024-06-01", tz="UTC")
Q = np.array(idx.to_period("Q").astype(str))
TFS = ["3min", "5min", "15min", "30min", "1h"]
GR = dict(AR.GR)
for tf in ("3min", "30min"): GR[tf] = G_.Grid(m1, tf)
NEXT = {"3min": ["15min", "1h"], "5min": ["15min", "1h"], "15min": ["1h", "4h"], "30min": ["1h", "4h"], "1h": ["4h"]}
HOR = {"3min": 720, "5min": 1440, "15min": 1440, "30min": 2880, "1h": 4320}
G4 = GR["4h"]; b4 = G4.bars
dep = D.trend_pullback_depths(b4.close.values, b4.high.values, b4.low.values, G4.F.atr, G4.F.bull, G4.F.bear)
ep_end = G4.pos[~np.isnan(dep)]; ep_d = dep[~np.isnan(dep)]
def trail_q(sig, q, n=20):
    c = np.searchsorted(ep_end, sig, side="right")
    return np.array([np.quantile(ep_d[max(0, x - n):x], q) if x >= 8 else 3.0 for x in c])
def rsi(c, n=2):
    d = np.diff(c, prepend=c[0]); up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False).mean(); dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).values
FAM = ["rsi2_10", "rsi2_5", "brk20", "pb30"]
def entries(tf, fam, nconf, sess):
    G = GR[tf]; F = G.F; c = G.bars.close.values
    htf = S.filters(F, 0, ("4h", "1D"), sess, 1), S.filters(F, 0, ("4h", "1D"), sess, -1)
    if fam.startswith("rsi2"):
        th = float(fam.split("_")[1]); r = rsi(c, 2)
        L = F.bull & (r < th); Sg = F.bear & (r > 100 - th)
    elif fam == "brk20":
        hh = G.bars.high.rolling(20).max().shift(1).values; ll = G.bars.low.rolling(20).min().shift(1).values
        L = F.bull & (c > hh); Sg = F.bear & (c < ll)
    else:
        L, Sg = S.signals(F, "pullback", 0, (), None, 30)
    L &= htf[0]; Sg &= htf[1]
    bi = np.where(L | Sg)[0]; d = np.where(L[bi], 1, -1); mi = G.pos[bi]
    keep = (idx[mi] >= H0) & (mi + 1 < len(idx))
    for ctf in NEXT[tf][:nconf]:
        H = GR[ctf]; keep &= np.where(d == 1, H.trend_up[mi], H.trend_dn[mi])
    bi, d, mi = bi[keep], d[keep], mi[keep]
    atr = F.atr[bi]
    mae, mfe, end = D.excursions(mi.astype(np.int64), d.astype(np.int64), G.c[mi], G.h, G.l, HOR[tf])
    return dict(bar=bi, dir=d, m1=mi, atr=atr, lvl=G.c[mi], mae_a=mae / atr, mfe_a=mfe / atr, end=end, atr4=G4.atr1[mi])
SETS = [(tf, fam, nc, sess) for tf in TFS for fam in FAM for nc in (0, 1, 2) for sess in (None, (7, 20)) if not (tf == "1h" and nc == 2)]
def job(si):
    tf, fam, nc, sess = SETS[si]
    Ent = entries(tf, fam, nc, sess)
    if len(Ent["m1"]) < 80: return []
    G = GR[tf]; live = idx[Ent["m1"]] >= S25; rows = []
    m = Ent["m1"].astype(np.int64); dd_ = Ent["dir"].astype(np.int64)
    for qsl in (0.5, 0.7):
        k = np.clip(D.rolling_quantile_known(m, Ent["end"], Ent["mae_a"], 60, qsl, 2.0), 0.5, 8.0); risk = k * Ent["atr"]
        for qtp in (0.2, 0.3, 0.5):
            r1 = np.clip(D.rolling_quantile_known(m, Ent["end"], Ent["mfe_a"], 60, qtp, 1.0) / k, 0.1, 3.0)
            for lock, qtr, f1 in itertools.product((0.1, 0.25), (0.5, 0.8), (0.5, 1e-9)):
                tw = trail_q(m, qtr) * Ent["atr4"]
                res = adv4.sim_dyn2(m, dd_, Ent["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c, G4.mgmt, G4.trend_up, G4.trend_dn,
                                    f1, lock, False, G_.COST_RT, 60 * 24 * 30)
                sel = np.where(live)[0]; take = A.greedy(m[sel], res[sel, 2].astype(np.int64)); s = sel[take]
                R = res[s, 0]
                if len(R) < 30: continue
                q = pd.Series(R).groupby(Q[m[s]]).sum(); w = R > 0
                eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
                rows.append(dict(si=si, tf=tf, fam=fam, nconf=nc, sess=str(sess), qsl=qsl, qtp=qtp, lock=lock, qtr=qtr, f1=round(f1, 1),
                                 n=len(R), win=w.mean() * 100, pf=R[w].sum() / -R[~w].sum() if (~w).any() else 99, R=R.sum(), dd=dd,
                                 qmin=q.min(), qpos=(q > 0).mean() * 100))
    return rows
if __name__ == "__main__":
    t = time.time()
    with Pool(4) as p:
        rows = [r for rr in p.imap_unordered(job, range(len(SETS))) for r in rr]
    pd.DataFrame(rows).to_parquet("dyn2_results.parquet"); print("sets", len(SETS), "configs", len(rows), "time", round(time.time() - t))
