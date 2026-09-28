"""Champion components on 2012-2022 XAUUSD 15m (broker server time ~UTC+2/3); execution on 15m bars."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import engine as E, gcdata as G_, strat as S, adv as A
base = E.load_m15()
base.index = base.index.tz_localize("UTC")
G_.TRADE_START = pd.Timestamp("2012-09-01", tz="UTC")
GR = {tf: G_.Grid(base, tf) for tf in ("15min", "1h", "4h")}
def volp(G):
    ar = pd.Series(G.F.atr, index=G.bars.index) / G.bars.close
    win = {"15min": 4 * 24 * 40, "1h": 24 * 40, "4h": 6 * 40}[G.tf]
    return ar.rolling(win, min_periods=win // 4).rank(pct=True).fillna(.5).values
VP = {tf: volp(G) for tf, G in GR.items()}
def run(tf, entry, pb, adx_rule, sess, k, adapt, r1, f1, lock, ttf, trail, brk, gba, gbg):
    G = GR[tf]
    L, Sg = S.signals(G.F, entry, 0, ("4h", "1D"), sess, pb)
    if adx_rule == "lt30": L &= G.F.adx < 30; Sg &= G.F.adx < 30
    bi = np.where(L | Sg)[0]; d = np.where(L[bi], 1, -1); m = G.pos[bi]
    keep = G.trade_ok[m] & (m + 1 < len(base)); bi, d, m = bi[keep], d[keep], m[keep]
    risk = G.F.atr[bi] * k * ((0.7 + 0.6 * VP[tf][bi]) if adapt else 1.0)
    T = GR[ttf]
    res = A.sim(m.astype(np.int64), d.astype(np.int64), G.c[m], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1, T.trend_up, T.trend_dn,
                r1, f1, lock, trail, brk, gba, gbg, G_.COST_RT, 4 * 24 * 15)
    take = A.greedy(m, res[:, 2].astype(np.int64))
    return pd.DataFrame(dict(t=base.index[m[take]], R=res[take, 0]))
def rep(t, label):
    R = t.R.values; w = R > 0; eq = np.cumsum(R); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    yr = t.groupby(t.t.dt.year).R.sum()
    print(f"{label}\n   n={len(R)} win={w.mean()*100:.0f}% PF={R[w].sum()/-R[~w].sum():.2f} totR={R.sum():+.0f} DD={dd:.0f}R  years+ {(yr>0).sum()}/{len(yr)}")
    print("   per year: " + " ".join(f"{y}:{v:+.0f}" for y, v in yr.items()))
# server time ~UTC+2/3 -> UTC 7-20 ~= server 9-22
h1 = run("1h", "pullback", 30, "lt30", (9, 22), 2.0, True, 0.5, 0.5, 0.25, "4h", 3.0, False, 3.0, 0.35)
rn = run("15min", "pullback", 40, "any", None, 1.5, True, 0.0, 0.0, 0.0, "4h", 2.0, True, 0.0, 0.0)
rep(h1, "H1 1h high-win (2012-2022)"); rep(rn, "RN15 15m runner (2012-2022)"); rep(pd.concat([h1, rn]).sort_values("t"), "H1 + RN15 (2012-2022)")
