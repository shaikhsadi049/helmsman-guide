import itertools, time, pickle, sys
import numpy as np, pandas as pd
from multiprocessing import Pool
import gcdata as G_, strat as S, adv as A, regime as RG

m1 = G_.load_1m()
TFS = ["5min", "15min", "1h", "4h"]
GR = {tf: G_.Grid(m1, tf) for tf in TFS}
SPLIT = np.datetime64(pd.Timestamp("2025-08-01", tz="UTC").tz_convert(None))
m1_t = m1.index.values.astype("datetime64[ns]")
y1_mask_m1 = m1.index.tz_convert(None).values < SPLIT
N_M1 = len(m1)


def volp_of(G):
    bars = G.bars
    atr_rel = pd.Series(G.F.atr, index=bars.index) / bars.close
    win = {"5min": 12 * 24 * 40, "15min": 4 * 24 * 40, "1h": 24 * 40, "4h": 6 * 40}[G.tf]
    return atr_rel.rolling(win, min_periods=win // 4).rank(pct=True).fillna(.5).values


VOLP = {tf: volp_of(GR[tf]) for tf in TFS}


def entry_set(tf, entry, pb, conf, adx_rule, sess):
    G = GR[tf]
    L, Sg = S.signals(G.F, entry, 0, ("4h", "1D"), sess, pb)
    adx = G.F.adx
    if adx_rule == "lt30":
        L &= adx < 30; Sg &= adx < 30
    elif adx_rule == "ge25":
        L &= adx >= 25; Sg &= adx >= 25
    bi = np.where(L | Sg)[0]
    dirs = np.where(L[bi], 1, -1)
    m1i = G.pos[bi]
    keep = G.trade_ok[m1i] & (m1i + 1 < N_M1)
    # multi-timeframe confluence: higher-TF EMA stack must already point the same way
    for ctf in conf:
        H = GR[ctf]
        up = H.trend_up[m1i]; dn = H.trend_dn[m1i]
        keep &= np.where(dirs == 1, up, dn)
    bi, dirs, m1i = bi[keep], dirs[keep], m1i[keep]
    return dict(bar=bi, dir=dirs, m1=m1i, atr=G.F.atr[bi], volp=VOLP[tf][bi], lvl=G.c[m1i])


ENTRY_SETS = []
for tf, entry, pb in [("5min", "pullback", 30), ("5min", "pullback", 40), ("15min", "pullback", 30), ("15min", "pullback", 40),
                      ("15min", "swing", 30), ("1h", "pullback", 30), ("1h", "pullback", 40), ("1h", "swing", 30)]:
    confs = {"5min": [(), ("15min",), ("15min", "1h")], "15min": [(), ("1h",)], "1h": [()]}[tf]
    adxs = ["any", "lt30"] if entry == "pullback" else ["any", "ge25"]
    for conf in confs:
        for ar in adxs:
            for sess in [None, (7, 20)]:
                ENTRY_SETS.append((tf, entry, pb, conf, ar, sess))

SLS = [(k, ad) for k in (0.75, 1.0, 1.5, 2.0, 3.0, 4.0) for ad in (False, True)]
TPS = [(0.0, 0.0, 0.0)] + [(r1, f1, lk) for r1 in (0.5, 0.75, 1.0) for f1 in (0.5, 0.7) for lk in (0.0, 0.25)]
RUN = []
for ttf in ("same", "1h", "4h"):
    for m in (0.0, 2.0, 3.0, 4.0, 6.0):
        for brk in (False, True):
            for gb in ((0.0, 0.0), (2.0, 0.5), (3.0, 0.35)):
                if m == 0 and not brk and gb[0] == 0:
                    continue          # runner with no exit rule -> skip
                RUN.append((ttf, m, brk, gb))


def stats(R):
    if len(R) < 8:
        return None
    w = R > 0
    gl = -R[~w].sum()
    eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    return (len(R), w.mean() * 100, R[w].sum() / gl if gl > 0 else 99, R.sum(), dd,
            R[w].mean() if w.any() else 0, R.max())


def job(args):
    es_i, (k, adapt) = args
    tf, entry, pb, conf, ar, sess = ENTRY_SETS[es_i]
    E = entry_set(tf, entry, pb, conf, ar, sess)
    if len(E["m1"]) < 30:
        return []
    order = np.argsort(E["m1"], kind="stable")
    for key in E: E[key] = E[key][order]
    risk = E["atr"] * k * ((0.7 + 0.6 * E["volp"]) if adapt else 1.0)
    G = GR[tf]
    rows = []
    in_y1 = y1_mask_m1[E["m1"]]
    for (r1, f1, lk), (ttf, m, brk, gb) in itertools.product(TPS, RUN):
        T = G if ttf == "same" else GR[ttf]
        res = A.sim(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c,
                    T.mgmt, T.atr1, T.trend_up, T.trend_dn, r1, f1, lk, m, brk, gb[0], gb[1], G_.COST_RT, 60 * 24 * 15)
        R = res[:, 0]; ex = res[:, 2].astype(np.int64)
        out = {}
        for nm, msk in (("y1", in_y1), ("y2", ~in_y1)):
            idx = np.where(msk)[0]
            take = A.greedy(E["m1"][idx], ex[idx])
            out[nm] = stats(R[idx][take])
        if out["y1"] is None or out["y2"] is None:
            continue
        rows.append((es_i, k, adapt, r1, f1, lk, ttf, m, brk, gb[0], gb[1]) + out["y1"] + out["y2"])
    return rows


COLS = ["es", "k", "adapt", "r1", "f1", "lock", "ttf", "trail", "brk", "gb_a", "gb_g",
        "n1", "win1", "pf1", "R1", "dd1", "aw1", "mx1", "n2", "win2", "pf2", "R2", "dd2", "aw2", "mx2"]

if __name__ == "__main__":
    t = time.time()
    jobs = [(i, s) for i in range(len(ENTRY_SETS)) for s in SLS]
    print("entry sets", len(ENTRY_SETS), "jobs", len(jobs), "exit combos/job", len(TPS) * len(RUN), flush=True)
    res = []
    with Pool(4) as p:
        for j, rows in enumerate(p.imap_unordered(job, jobs, chunksize=1)):
            res.extend(rows)
            if j % 50 == 0:
                print(j, "/", len(jobs), round(time.time() - t), "s", flush=True)
    df = pd.DataFrame(res, columns=COLS)
    df.to_parquet("adv_results.parquet")
    pickle.dump(ENTRY_SETS, open("adv_entry_sets.pkl", "wb"))
    print("done", len(df), round(time.time() - t), "s")
