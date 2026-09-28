import itertools, time, sys, numpy as np, pandas as pd
from multiprocessing import Pool
import engine as E, strat as S

TF = sys.argv[1] if len(sys.argv) > 1 else "15m"
df = E.load_m15()
if TF != "15m":
    df = E.resample(df, TF)
F = S.Feat(df)
SPLIT = pd.Timestamp("2019-01-01")
isIS = (df.index < SPLIT)

ENTRIES = [("flip_alt", 30), ("flip", 30), ("swing", 30), ("pullback", 30), ("pullback", 40), ("pullback", 60)]
ADX = [0, 20, 25, 30]
HTF = {"15m": [(), ("1h",), ("4h",), ("1D",), ("1h", "4h"), ("4h", "1D")],
       "1h":  [(), ("4h",), ("1D",), ("4h", "1D")],
       "4h":  [(), ("1D",)]}[TF]
SESS = [None, (9, 22), (10, 19)] if TF in ("15m", "1h") else [None]
SL = [("pct", .25), ("pct", .5), ("atr", 1.0), ("atr", 1.5), ("atr", 2.0), ("atr", 3.0), ("swing", 8), ("swing", 12)]
EXITS = ["orig4", "orig4_be", "tp:1", "tp:1.5", "tp:2", "tp:3", "brk", "trail:2", "trail:3",
         "half:1:2", "half:1:3", "half:1:0", "scale:0.5:0.5:2", "tp_brk:2", "tp_brk:3"]

def summ(tr, sel):
    t = tr[sel]
    if len(t) < 20:
        return None
    pnl = t[:, 3]; R = pnl / t[:, 4]
    gl = -pnl[pnl <= 0].sum()
    eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    return len(t), (pnl > 0).mean() * 100, pnl[pnl > 0].sum() / gl if gl > 0 else 99, R.mean(), R.sum(), dd

def job(sig):
    (entry, pb), adx, htf, sess = sig
    L, Sg = S.signals(F, entry, adx, htf, sess, pb)
    rows = []
    for (slm, slv), ex in itertools.product(SL, EXITS):
        if slm == "swing":
            dl, ds = S.stops(F, "swing", swing_n=int(slv))
        else:
            dl, ds = S.stops(F, slm, slv)
        x = S.exit_cfg(ex)
        tr = E.run(F.o, F.h, F.l, F.c, L, Sg, F.bull, F.bear, dl, ds, np.array(x["tp_r"], float),
                   np.array(x["tp_frac"], float), x["be_leg"], x["trail"], F.atr, x["brk"], True, S.COST_RT)
        if len(tr) < 40:
            continue
        ins = isIS[tr[:, 0].astype(int)]
        a = summ(tr, ins); b = summ(tr, ~ins)
        if a is None or b is None:
            continue
        yrs = pd.Series(tr[:, 3] / tr[:, 4], index=df.index[tr[:, 0].astype(int)].year).groupby(level=0).sum()
        rows.append(dict(entry=entry, pb=pb, adx=adx, htf="+".join(htf) or "-", sess=str(sess), sl=f"{slm}{slv}", exit=ex,
                         n_is=a[0], win_is=a[1], pf_is=a[2], exp_is=a[3], R_is=a[4], dd_is=a[5],
                         n_oos=b[0], win_oos=b[1], pf_oos=b[2], exp_oos=b[3], R_oos=b[4], dd_oos=b[5],
                         yrs_pos=(yrs > 0).mean() * 100))
    return rows

if __name__ == "__main__":
    t = time.time()
    sigs = list(itertools.product(ENTRIES, ADX, HTF, SESS))
    with Pool(4) as p:
        res = [r for rows in p.imap_unordered(job, sigs, chunksize=2) for r in rows]
    out = pd.DataFrame(res)
    out.to_csv(f"grid_{TF}.csv", index=False)
    print(TF, "configs:", len(out), "time:", round(time.time() - t), "s")
