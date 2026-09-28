import numpy as np, pandas as pd, warnings, pickle
warnings.filterwarnings("ignore")
import lightgbm as lgb
import adv_run as AR, adv as A, gcdata as G_, dxy, regime as RG
from adv_port import ES, SPLIT
exec("\n".join(l for l in open("adv_port_run.py").read().split("\n") if l.startswith(("df = pd.read","df[\"tf\"]","def es_id","    return ES.index","def row","    q = df","    for k, v","        q = q[","    assert","    return q.iloc"))))
exec(open("adv_port_run.py").read().split("PICKS = ")[1].split("}\n")[0].join(["PICKS = ", "}\n"]))
m1 = AR.m1; U = dxy.USD(m1.index); up1 = U.htf_up("1h"); corr = U.corr(m1.close.values)
ER = {tf: RG.efficiency_ratio(AR.GR[tf].bars.close, 20).values for tf in AR.TFS}

def features(tf, E):
    G = AR.GR[tf]; b = E["bar"]; i = E["m1"]; d = E["dir"]
    e = G.F.emas; atr = G.F.atr[b]
    f = pd.DataFrame(dict(
        dir=d, adx=G.F.adx[b], er=ER[tf][b], volp=E["volp"],
        spread=((e[30] - e[60]).abs().values[b] / atr), slope=((e[60] - e[60].shift(10)).values[b] / atr) * d,
        dist30=(G.c[i] - e[30].values[b]) / atr * d, mom20=(G.F.c[b] - G.F.c[np.maximum(b - 20, 0)]) / atr * d,
        hour=m1.index[i].hour, dow=m1.index[i].dayofweek,
        h1=np.where(d == 1, AR.GR["1h"].trend_up[i], AR.GR["1h"].trend_dn[i]).astype(int),
        h4=np.where(d == 1, AR.GR["4h"].trend_up[i], AR.GR["4h"].trend_dn[i]).astype(int),
        adx4=AR.GR["4h"].F.adx[AR.GR["4h"].idx[i]], volp4=None,
        usd_corr=np.where(U.avail[i], corr[i], np.nan),
        usd_against=np.where(U.avail[i], np.where(d == 1, up1[i] == 0, up1[i] == 1).astype(float), np.nan)))
    f["volp4"] = AR.VOLP["4h"][AR.GR["4h"].idx[i]]
    return f

def strategy(r):
    tf, entry, pb, conf, ar, sess = ES[int(r.es)]
    E = AR.entry_set(tf, entry, pb, conf, ar, sess)
    o = np.argsort(E["m1"], kind="stable")
    for k in E: E[k] = E[k][o]
    risk = E["atr"] * r.k * ((0.7 + 0.6 * E["volp"]) if r.adapt else 1.0)
    G = AR.GR[tf]; T = G if r.ttf == "same" else AR.GR[r.ttf]
    res = A.sim(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1,
                T.trend_up, T.trend_dn, r.r1, r.f1, r.lock, r.trail, bool(r.brk), r.gb_a, r.gb_g, G_.COST_RT, 60 * 24 * 15)
    return tf, E, res

def evalset(E, res, keep, label):
    idx = np.where(keep)[0]
    take = A.greedy(E["m1"][idx], res[idx, 2].astype(np.int64))
    R = res[idx[take], 0]; t = m1.index[E["m1"][idx[take]]]
    y2 = t >= SPLIT; R2 = R[y2]
    w = R2 > 0
    return f"{label:22s} Y2: n={len(R2):3d} win={w.mean()*100:3.0f}% PF={R2[w].sum()/-R2[~w].sum():.2f} R={R2.sum():+6.1f}"

MONTHS = pd.date_range("2025-08-01", "2026-08-01", freq="MS", tz="UTC")
for name, r in PICKS.items():
    tf, E, res = strategy(r)
    X = features(tf, E); R = res[:, 0]
    t_in = m1.index[E["m1"]]; t_out = m1.index[res[:, 2].astype(int)]
    out = {}
    for tgt_name, y in (("R>0", (R > 0).astype(int)), ("R>=1", (R >= 1).astype(int))):
        for use_usd in (False, True):
            cols = [c for c in X.columns if use_usd or not c.startswith("usd")]
            p = np.full(len(R), np.nan); thr = np.full(len(R), np.nan)
            for a, b in zip(MONTHS[:-1], MONTHS[1:]):
                tr = np.asarray(t_out < a); te = np.asarray((t_in >= a) & (t_in < b))
                if te.sum() == 0 or tr.sum() < 60 or y[tr].min() == y[tr].max(): continue
                g = lgb.LGBMClassifier(n_estimators=200, num_leaves=7, min_child_samples=20, learning_rate=0.03,
                                       subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1).fit(X[cols][tr], y[tr])
                p[te] = g.predict_proba(X[cols][te])[:, 1]
                thr[te] = np.quantile(g.predict_proba(X[cols][tr])[:, 1], 0.4)   # drop the worst-looking 40 %
            out[(tgt_name, use_usd)] = (~(p < thr))                     # NaN (no model yet) -> keep
    print(f"\n{name}")
    print("  " + evalset(E, res, np.ones(len(R), bool), "no ML"))
    for (tg, uu), keep in out.items():
        print("  " + evalset(E, res, keep, f"ML target {tg} {'+USD' if uu else ''}"))
