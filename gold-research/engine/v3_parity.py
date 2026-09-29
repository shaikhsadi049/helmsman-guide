"""EA v3 parity: the 7 slots exactly as written in the EA spec strings, research vs EA-style calculations."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import dyn2_run as R2, adv3 as D, adv4, adv as A, gcdata as G_, strat as S
idx = R2.idx
SLOTS = [  # tf, fam, nconf, sess, qsl, qtp, lock, qtr, f1
 ("30min", "pb30",    1, (7, 20), .7, .3, .25, .8, 0), ("15min", "brk20", 2, None, .5, .2, .10, .8, 0),
 ("3min",  "rsi2_10", 2, (7, 20), .7, .2, .10, .5, .5), ("30min", "brk20", 0, None, .7, .2, .25, .8, 0),
 ("5min",  "pb30",    2, (7, 20), .5, .5, .25, .5, .5), ("3min",  "rsi2_5", 2, (7, 20), .7, .2, .10, .5, .5),
 ("3min",  "brk20",   2, None, .7, .2, .10, .8, 0)]
def sma_atr(b, n=14):
    pc = b.close.shift(1); tr = pd.concat([b.high - b.low, (b.high - pc).abs(), (b.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().bfill().values
def mt5_rsi(c, n=2):   # MT5 iRSI: first value SMA, then Wilder smoothing
    d = np.diff(c, prepend=c[0]); up = np.maximum(d, 0); dn = np.maximum(-d, 0)
    au = np.zeros(len(c)); ad = np.zeros(len(c)); au[n] = up[1:n + 1].mean(); ad[n] = dn[1:n + 1].mean()
    for i in range(n + 1, len(c)): au[i] = (au[i - 1] * (n - 1) + up[i]) / n; ad[i] = (ad[i - 1] * (n - 1) + dn[i]) / n
    with np.errstate(divide="ignore", invalid="ignore"): r = np.where(ad == 0, 100.0, 100 - 100 / (1 + au / ad))
    r[:n] = 50; return r
ATRS = {tf: sma_atr(R2.GR[tf].bars) for tf in ("3min", "5min", "15min", "30min", "4h")}
def entries_ea(tf, fam, nc, sess):
    """Same signal families, computed with MT5 RSI; excursions measured on TF bars; ATR = SMA of TR."""
    G = R2.GR[tf]; F = G.F; c = G.bars.close.values
    htfL, htfS = S.filters(F, 0, ("4h", "1D"), sess, 1), S.filters(F, 0, ("4h", "1D"), sess, -1)
    if fam.startswith("rsi2"):
        th = float(fam.split("_")[1]); r = mt5_rsi(c, 2); L = F.bull & (r < th); Sg = F.bear & (r > 100 - th)
    elif fam == "brk20":
        hh = G.bars.high.rolling(20).max().shift(1).values; ll = G.bars.low.rolling(20).min().shift(1).values
        L = F.bull & (c > hh); Sg = F.bear & (c < ll)
    else:
        L, Sg = S.signals(F, "pullback", 0, (), None, 30)
    L &= htfL; Sg &= htfS
    bi = np.where(L | Sg)[0]; d = np.where(L[bi], 1, -1); mi = G.pos[bi]
    keep = (idx[mi] >= R2.H0) & (mi + 1 < len(idx))
    for ctf in R2.NEXT[tf][:nc]:
        H = R2.GR[ctf]; keep &= np.where(d == 1, H.trend_up[mi], H.trend_dn[mi])
    bi, d, mi = bi[keep], d[keep], mi[keep]
    atr = ATRS[tf][bi]; H_, L_ = G.bars.high.values, G.bars.low.values
    hb = max(1, R2.HOR[tf] // int(pd.Timedelta(tf).total_seconds() // 60))
    mae = np.zeros(len(bi)); mfe = np.zeros(len(bi)); end = np.zeros(len(bi), np.int64)
    for k, (b, dd, lv) in enumerate(zip(bi, d, c[bi])):
        s = slice(b + 1, min(len(H_), b + 1 + hb))
        if s.start >= s.stop: end[k] = G.pos[-1]; continue
        mae[k] = max(0, (lv - L_[s].min()) if dd == 1 else (H_[s].max() - lv)); mfe[k] = max(0, (H_[s].max() - lv) if dd == 1 else (lv - L_[s].min()))
        end[k] = G.pos[min(len(H_) - 1, b + hb)]
    atr4 = ATRS["4h"][R2.G4.idx[mi]]
    return dict(bar=bi, dir=d, m1=mi, atr=atr, lvl=G.c[mi], mae_a=mae / atr, mfe_a=mfe / atr, end=end, atr4=atr4)
def run(slot, ea, sess_override="keep"):
    tf, fam, nc, sess, qsl, qtp, lock, qtr, f1 = slot
    if sess_override != "keep": sess = sess_override
    Ent = entries_ea(tf, fam, nc, sess) if ea else R2.entries(tf, fam, nc, sess)
    G = R2.GR[tf]; m = Ent["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, Ent["end"], Ent["mae_a"], 60, qsl, 2.0), 0.5, 8.0); risk = k * Ent["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, Ent["end"], Ent["mfe_a"], 60, qtp, 1.0) / k, 0.1, 3.0)
    tw = R2.trail_q(m, qtr) * Ent["atr4"]
    res = adv4.sim_dyn2(m, Ent["dir"].astype(np.int64), Ent["lvl"], risk, r1, tw, G.o, G.h, G.l, G.c, R2.G4.mgmt, R2.G4.trend_up, R2.G4.trend_dn,
                        f1 if f1 > 0 else 1e-9, lock, False, G_.COST_RT, 60 * 24 * 30)
    sel = np.where(idx[m] >= R2.S25)[0]; take = A.greedy(m[sel], res[sel, 2].astype(np.int64)); s = sel[take]
    return pd.DataFrame(dict(t_in=idx[m[s]], t_out=idx[res[s, 2].astype(int)], R=res[s, 0]))
def rep(T, label):
    T = T.sort_values("t_out"); R = T.R.values; w = R > 0; eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    q = T.groupby(T.t_in.dt.to_period("Q").astype(str)).R.sum()
    return f"{label:34s} trades {len(R):4d} win {w.mean()*100:3.0f}% PF {R[w].sum()/-R[~w].sum():5.2f} totR {R.sum():+6.1f} DD {dd:4.1f}R quarters+ {(q>0).sum()}/{len(q)}"
if __name__ == "__main__":
    print("per slot: research | EA-style")
    RS, EA = [], []
    for i, sl in enumerate(SLOTS):
        a = run(sl, False); b = run(sl, True); RS.append(a); EA.append(b)
        print(f"S{i+1} " + rep(a, f"{sl[0]} {sl[1]} research") + "\n   " + rep(b, "EA-style"))
    print("\nPORTFOLIO 7  " + rep(pd.concat(RS), "research"))
    print("PORTFOLIO 7  " + rep(pd.concat(EA), "EA-style"))
    s6all = run(SLOTS[5], True, sess_override=None); s6ses = EA[5]
    print("\nS6 session vs all-day (EA-style): " + rep(s6ses, "session") + " | " + rep(s6all, "all day"))
    print("PORTFOLIO 7 with S6 all day " + rep(pd.concat(EA[:5] + [s6all] + EA[6:]), "EA-style"))
