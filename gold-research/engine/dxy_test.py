import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import adv_run as AR, adv as A, gcdata as G_, dxy
m1 = AR.m1; U = dxy.USD(m1.index)
END = pd.Timestamp("2026-01-01", tz="UTC"); SPLIT = pd.Timestamp("2025-08-01", tz="UTC")
up1 = U.htf_up("1h"); up4 = U.htf_up("4h"); corr = U.corr(m1.close.values)
stk = {tf: U.stack(tf) for tf in ("5min", "15min", "1h")}

def filt_mask(name, E, tf):
    i = E["m1"]; d = E["dir"]
    usd_ok = U.avail[i]
    if name == "none": return usd_ok
    down1 = up1[i] == 0; upx1 = up1[i] == 1; down4 = up4[i] == 0; upx4 = up4[i] == 1
    against1 = np.where(d == 1, down1, upx1); against4 = np.where(d == 1, down4, upx4)
    st = stk[tf][i]
    if name == "usd1h_against": return usd_ok & against1
    if name == "usd4h_against": return usd_ok & against4
    if name == "usd1h+4h_against": return usd_ok & against1 & against4
    if name == "usd_stack_against": return usd_ok & (st == -d)
    if name == "block_usd_stack_with": return usd_ok & (st != d)
    if name == "corr_gate+usd1h": return usd_ok & (np.where(corr[i] < -0.2, against1, True))
    raise ValueError(name)
FILTERS = ["none", "usd1h_against", "usd4h_against", "usd1h+4h_against", "usd_stack_against", "block_usd_stack_with", "corr_gate+usd1h"]

def run(row, fname):
    tf, entry, pb, conf, ar, sess = AR.ENTRY_SETS[int(row.es)]
    E = AR.entry_set(tf, entry, pb, conf, ar, sess)
    o = np.argsort(E["m1"], kind="stable")
    for k in E: E[k] = E[k][o]
    keep = filt_mask(fname, E, tf) & (m1.index[E["m1"]] < END)
    for k in E: E[k] = E[k][keep]
    if len(E["m1"]) < 5: return None
    risk = E["atr"] * row.k * ((0.7 + 0.6 * E["volp"]) if row.adapt else 1.0)
    G = AR.GR[tf]; T = G if row.ttf == "same" else AR.GR[row.ttf]
    res = A.sim(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1,
                T.trend_up, T.trend_dn, row.r1, row.f1, row.lock, row.trail, bool(row.brk), row.gb_a, row.gb_g, G_.COST_RT, 60 * 24 * 15)
    take = A.greedy(E["m1"], res[:, 2].astype(np.int64))
    return pd.DataFrame(dict(t=m1.index[E["m1"][take]], R=res[take, 0]))

def st(R):
    if len(R) < 3: return (len(R), np.nan, np.nan, R.sum() if len(R) else 0)
    w = R > 0; gl = -R[~w].sum()
    return (len(R), w.mean() * 100, R[w].sum() / gl if gl > 0 else 99, R.sum())

if __name__ == "__main__":
    df = pd.read_parquet("adv_results.parquet")
    df["tf"] = [AR.ENTRY_SETS[i][0] for i in df.es]
    # a-priori sample: top 60 per timeframe by Y1 R/DD with >=40 trades (no Y2 peeking)
    df["key"] = df.R1 / df.dd1.clip(lower=3)
    sample = pd.concat([d[d.n1 >= 40].sort_values("key", ascending=False).head(60) for _, d in df.groupby("tf")])
    rows = []
    for _, r in sample.iterrows():
        for f in FILTERS:
            t = run(r, f)
            if t is None: continue
            a = st(t.R[t.t < SPLIT].values); b = st(t.R[t.t >= SPLIT].values)
            rows.append(dict(tf=r.tf, cfg=_, filt=f, n1=a[0], win1=a[1], pf1=a[2], R1=a[3], n2=b[0], win2=b[1], pf2=b[2], R2=b[3]))
    out = pd.DataFrame(rows); out.to_csv("dxy_test.csv", index=False)
    base = out[out.filt == "none"].set_index("cfg")
    print("Window: Aug-2024..Dec-2025 (USD data). P1 = Aug24-Jul25, P2 = Aug25-Dec25. 180 configs (top-60/TF by Y1).")
    for f in FILTERS[1:]:
        x = out[out.filt == f].set_index("cfg").join(base, rsuffix="_b")
        print(f"\n{f:22s}")
        for tf, g in x.groupby("tf"):
            print(f"  {tf:6s} trades kept {g.n1.sum()/g.n1_b.sum()*100:3.0f}% | win change P1 {np.nanmedian(g.win1-g.win1_b):+5.1f}pp P2 {np.nanmedian(g.win2-g.win2_b):+5.1f}pp"
                  f" | PF change P1 {np.nanmedian(g.pf1-g.pf1_b):+.2f} P2 {np.nanmedian(g.pf2-g.pf2_b):+.2f} | R change P1 {np.median(g.R1-g.R1_b):+6.1f} P2 {np.median(g.R2-g.R2_b):+6.1f}"
                  f" | configs improved (PF, both periods) {((g.pf1>g.pf1_b)&(g.pf2>g.pf2_b)).mean()*100:3.0f}%")
