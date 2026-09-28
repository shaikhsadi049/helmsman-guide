"""Same config space as adv_run (15m / 1h entries), run on 2012-2022 XAUUSD 15m bars (execution on 15m bars)."""
import itertools, time, numpy as np, pandas as pd, warnings
from multiprocessing import Pool
warnings.filterwarnings("ignore")
import engine as E, gcdata as G_, strat as S, adv as A
import adv_run as AR  # for ENTRY_SETS / SLS / TPS / RUN definitions
base = E.load_m15(); base.index = base.index.tz_localize("UTC")
G_.TRADE_START = pd.Timestamp("2012-09-01", tz="UTC")
GR = {tf: G_.Grid(base, tf) for tf in ("15min", "1h", "4h")}
def volp(G):
    ar = pd.Series(G.F.atr, index=G.bars.index) / G.bars.close
    win = {"15min": 4 * 24 * 40, "1h": 24 * 40, "4h": 6 * 40}[G.tf]
    return ar.rolling(win, min_periods=win // 4).rank(pct=True).fillna(.5).values
VP = {tf: volp(G) for tf, G in GR.items()}
ERA = {"A 2012-16": (2012, 2016), "B 2017-19": (2017, 2019), "C 2020-22": (2020, 2022)}
yr_of = base.index.year.values
def entries(es):
    tf, entry, pb, conf, ar, sess = AR.ENTRY_SETS[es]
    G = GR[tf]
    sess2 = None if sess is None else (sess[0] + 2, sess[1] + 2)   # UTC -> broker server time
    L, Sg = S.signals(G.F, entry, 0, ("4h", "1D"), sess2, pb)
    if ar == "lt30": L &= G.F.adx < 30; Sg &= G.F.adx < 30
    if ar == "ge25": L &= G.F.adx >= 25; Sg &= G.F.adx >= 25
    bi = np.where(L | Sg)[0]; d = np.where(L[bi], 1, -1); m = G.pos[bi]
    keep = G.trade_ok[m] & (m + 1 < len(base))
    for ctf in conf:
        H = GR[ctf]; keep &= np.where(d == 1, H.trend_up[m], H.trend_dn[m])
    return tf, bi[keep], d[keep], m[keep]
def job(args):
    es, (k, adapt) = args
    tf, bi, d, m = entries(es)
    if len(m) < 50: return []
    G = GR[tf]; risk = G.F.atr[bi] * k * ((0.7 + 0.6 * VP[tf][bi]) if adapt else 1.0)
    yrs = yr_of[m]; rows = []
    for (r1, f1, lk), (ttf, mm, brk, gb) in itertools.product(AR.TPS, AR.RUN):
        T = G if ttf == "same" else GR[ttf]
        res = A.sim(m.astype(np.int64), d.astype(np.int64), G.c[m], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1, T.trend_up, T.trend_dn,
                    r1, f1, lk, mm, brk, gb[0], gb[1], G_.COST_RT, 4 * 24 * 15)
        take = A.greedy(m, res[:, 2].astype(np.int64)); R = res[take, 0]; y = yrs[take]
        row = [es, k, adapt, r1, f1, lk, ttf, mm, brk, gb[0], gb[1]]
        for nm, (a, b) in ERA.items():
            x = R[(y >= a) & (y <= b)]; w = x > 0
            row += [len(x), x.sum(), (x[w].sum() / -x[~w].sum()) if (~w).any() else 99, w.mean() * 100 if len(x) else np.nan]
        yrR = pd.Series(R).groupby(y).sum()
        row += [(yrR > 0).mean() * 100]
        rows.append(row)
    return rows
if __name__ == "__main__":
    t = time.time()
    es_ids = [i for i, e in enumerate(AR.ENTRY_SETS) if e[0] in ("15min", "1h")]
    jobs = [(i, s) for i in es_ids for s in AR.SLS]
    print("jobs", len(jobs), flush=True)
    out = []
    with Pool(4) as p:
        for j, rows in enumerate(p.imap_unordered(job, jobs, chunksize=1)):
            out += rows
            if j % 50 == 0: print(j, round(time.time() - t), flush=True)
    cols = ["es","k","adapt","r1","f1","lock","ttf","trail","brk","gb_a","gb_g"]
    for nm in ERA: cols += [f"n_{nm[0]}", f"R_{nm[0]}", f"pf_{nm[0]}", f"win_{nm[0]}"]
    cols += ["yrs_pos"]
    pd.DataFrame(out, columns=cols).to_parquet("decade_grid.parquet")
    print("done", len(out), round(time.time() - t))
