"""Mean-reversion / sideways families on 5m..1h, market-measured SL/TP, judged on 2025-01..2026-07 by quarter,
and by how they do in the months the trend portfolio (S1-S6) is flat."""
import numpy as np, pandas as pd, warnings, itertools, pickle
warnings.filterwarnings("ignore")
import dyn2_run as R2, adv3 as D, adv4, adv as A, gcdata as G_
idx = R2.idx; m1 = R2.m1
# daily trend score (same as EA v3.20), known at the previous daily close
d = m1.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
pc = d.close.shift(); trd = np.maximum(d.high - d.low, np.maximum((d.high - pc).abs(), (d.low - pc).abs())).rolling(14).mean()
dts = ((d.close - d.close.ewm(span=50, adjust=False).mean()).abs() / trd).rolling(250, min_periods=125).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True).shift(1)
def dt_at(mi): return np.nan_to_num(dts.reindex(pd.DatetimeIndex(idx[mi]).floor("1D")).values, nan=0.5)
MRH = {"5min": 36, "15min": 24, "30min": 16, "1h": 12}           # horizon in TF bars (~3h..12h)
def rsi2(c):
    x = np.diff(c, prepend=c[0]); up = pd.Series(np.maximum(x, 0)).ewm(alpha=.5, adjust=False).mean(); dn = pd.Series(np.maximum(-x, 0)).ewm(alpha=.5, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).values
def raw_signals(tf, fam):
    G = R2.GR[tf]; b = G.bars; c = b.close.values
    if fam.startswith("z"):
        th = float(fam[1:]); ma = b.close.rolling(20).mean(); sd = b.close.rolling(20).std(); z = ((b.close - ma) / sd).values
        L = z < -th; S = z > th
    elif fam == "rsi2":
        r = rsi2(c); L = r < 5; S = r > 95
    elif fam == "fbo":   # false breakout: the bar pierced the 20-bar extreme but closed back inside
        hh = b.high.rolling(20).max().shift(1).values; ll = b.low.rolling(20).min().shift(1).values
        S = (b.high.values > hh) & (c < hh); L = (b.low.values < ll) & (c > ll)
    elif fam == "ext3":  # 3 closes in a row stretched > 1 ATR from EMA20, then a reversal close
        e = b.close.ewm(span=20, adjust=False).mean().values; a = G.F.atr; dev = (c - e) / a
        up = pd.Series(dev > 1).rolling(3).sum().shift(1).values == 3; dn = pd.Series(dev < -1).rolling(3).sum().shift(1).values == 3
        S = up & (c < b.open.values); L = dn & (c > b.open.values)
    L = np.nan_to_num(L).astype(bool); S = np.nan_to_num(S).astype(bool)
    return L, S
def entries(tf, fam, regime, sess):
    G = R2.GR[tf]; F = G.F
    L, S = raw_signals(tf, fam)
    if regime == "nostack": ok = ~F.bull & ~F.bear; L &= ok; S &= ok
    if regime == "no4h":    # 4H trend not aligned either way
        pass
    if sess: h = F.hour; ok = (h >= 7) & (h < 20); L &= ok; S &= ok
    bi = np.where(L | S)[0]; dr = np.where(L[bi], 1, -1); mi = G.pos[bi]
    keep = (idx[mi] >= R2.H0) & (mi + 1 < len(idx))
    if regime == "no4h": keep &= ~R2.G4.trend_up[mi] & ~R2.G4.trend_dn[mi]
    if regime == "dweak": keep &= dt_at(mi) < 0.5
    if regime == "with4h": keep &= np.where(dr == 1, R2.G4.trend_up[mi], R2.G4.trend_dn[mi])   # buy dips only in 4H uptrend (reference)
    bi, dr, mi = bi[keep], dr[keep], mi[keep]
    atr = F.atr[bi]; hb = MRH[tf]; H_, L_ = G.bars.high.values, G.bars.low.values; lv = G.bars.close.values[bi]
    mae = np.zeros(len(bi)); mfe = np.zeros(len(bi)); end = np.zeros(len(bi), np.int64)
    for k, (b0, dd) in enumerate(zip(bi, dr)):
        s = slice(b0 + 1, min(len(H_), b0 + 1 + hb))
        if s.start >= s.stop: end[k] = G.pos[-1]; continue
        mae[k] = max(0, (lv[k] - L_[s].min()) if dd == 1 else (H_[s].max() - lv[k])); mfe[k] = max(0, (H_[s].max() - lv[k]) if dd == 1 else (lv[k] - L_[s].min()))
        end[k] = G.pos[min(len(H_) - 1, b0 + hb)]
    return dict(dir=dr, m1=mi, atr=atr, lvl=G.c[mi], mae_a=mae / atr, mfe_a=mfe / atr, end=end)
def run(tf, fam, regime, sess, qsl, qtp, cost=G_.COST_RT):
    E = entries(tf, fam, regime, sess)
    if len(E["m1"]) < 50: return None
    G = R2.GR[tf]; m = E["m1"].astype(np.int64)
    k = np.clip(D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, qsl, 2.0), 0.3, 8.0); risk = k * E["atr"]
    r1 = np.clip(D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, qtp, 1.0) / k, 0.1, 5.0)
    hor = MRH[tf] * int(pd.Timedelta(tf).total_seconds() // 60)
    res = adv4.sim_dyn2(m, E["dir"].astype(np.int64), E["lvl"], risk, r1, np.zeros(len(m)), G.o, G.h, G.l, G.c, R2.G4.mgmt, R2.G4.trend_up, R2.G4.trend_dn,
                        1.0, 0.0, False, cost, hor)
    sel = np.where(idx[m] >= R2.S25)[0]; take = A.greedy(m[sel], res[sel, 2].astype(np.int64)); s = sel[take]
    return pd.DataFrame(dict(t_in=m[s] + 1, t_out=res[s, 2].astype(np.int64), R=res[s, 0], risk=risk[s], time=idx[m[s]]))
if __name__ == "__main__":
    # trend portfolio monthly R (S1-S6, one position per slot) for correlation
    T = pd.read_parquet("../trades_v3_reg.parquet"); T = T[T.slot != 6]
    keep = np.zeros(len(T), bool); bu = {}
    for i, (s, a, b) in enumerate(zip(T.slot, T.t_in, T.t_out)):
        if bu.get(s, -1) < a: keep[i] = True; bu[s] = b
    X = T[keep]; TM = X.groupby(X.time.dt.tz_localize(None).dt.to_period("M")).R.sum()
    flat = TM.index[TM < 10]
    print("trend-portfolio flat months:", [str(p) for p in flat])
    rows = []; keepT = {}
    for tf, fam, regime, sess, qsl, qtp in itertools.product(["5min", "15min", "30min", "1h"], ["z2", "z2.5", "rsi2", "fbo", "ext3"],
                                                             ["none", "nostack", "no4h", "dweak", "with4h"], [False, True], [0.7, 0.9], [0.3, 0.5, 0.7]):
        r = run(tf, fam, regime, sess, qsl, qtp)
        if r is None or len(r) < 30: continue
        R = r.R.values; w = R > 0; Rc = R - 1.66 / r.risk.values
        mo = r.groupby(r.time.dt.tz_localize(None).dt.to_period("M")).R.sum().reindex(TM.index, fill_value=0)
        q = r.groupby(r.time.dt.tz_localize(None).dt.to_period("Q")).R.sum()
        eq = np.cumsum(R); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
        key = (tf, fam, regime, sess, qsl, qtp); keepT[key] = r
        rows.append(dict(tf=tf, fam=fam, regime=regime, sess=sess, qsl=qsl, qtp=qtp, n=len(R), win=w.mean(), PF=R[w].sum() / max(1e-9, -R[~w].sum()),
                         sumR=R.sum(), dd=dd, qpos=(q > 0).sum(), nq=len(q), cost2=Rc.sum(), corr=np.corrcoef(mo.values, TM.values)[0, 1],
                         flatR=mo.reindex(flat).sum()))
        print(len(rows), key, f"n {len(R)} win {w.mean():.2f} PF {rows[-1]['PF']:.2f} sumR {R.sum():+.1f} q+ {(q>0).sum()}/{len(q)}", flush=True)
    df = pd.DataFrame(rows); df.to_parquet("../mr_grid.parquet"); pickle.dump(keepT, open("../mr_trades.pkl", "wb"))
