import pickle, warnings, numpy as np, pandas as pd
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings("ignore")
import gcdata as G_
m1 = G_.load_1m()
data = pickle.load(open("regime_sims.pkl", "rb"))
FEAT = ["adx", "er", "volp", "spread", "slope", "hour", "dir"]
def s(x):
    if len(x) == 0: return "none"
    pf = x[x > 0].sum() / -x[x <= 0].sum()
    eq = np.cumsum(x); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    return f"n={len(x):4d} win={np.mean(x>0)*100:3.0f}% PF={pf:.2f} exp={x.mean():+.3f}R tot={x.sum():+7.1f}R DD={dd:5.1f}R"
CASES = [(("5min","pullback"), (2.0,"tr6")), (("5min","pullback"), (1.0,"h1tr3")), (("15min","pullback"), (4.0,"tr6")),
         (("15min","pullback"), (2.0,"h1brk")), (("1h","pullback"), (1.0,"tr3")), (("15min","swing"), (0.75,"brk"))]
for key, cfg in CASES:
    ev, sims = data[key]
    r = sims[cfg]
    ev = ev.copy(); ev["R"] = r[:, 0]
    exit_i = np.clip(ev.m1.values + 1 + r[:, 3].astype(int), 0, len(m1) - 1)
    ev["exit_t"] = m1.index[exit_i]
    X = ev[FEAT].fillna(0.5).values; y = (ev.R > 0).astype(int).values
    months = pd.date_range("2025-08-01", "2026-08-01", freq="MS", tz="UTC")
    p_gbm = np.full(len(ev), np.nan); p_lr = np.full(len(ev), np.nan); thr_g = {}; thr_l = {}
    for a, b in zip(months[:-1], months[1:]):
        tr = (ev.exit_t < a).values            # purged: only trades already closed
        te = ((ev.time >= a) & (ev.time < b)).values
        if te.sum() == 0 or tr.sum() < 80: continue
        g = lgb.LGBMClassifier(n_estimators=150, num_leaves=7, min_child_samples=25, learning_rate=0.03,
                               subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1)
        g.fit(X[tr], y[tr])
        lr = LogisticRegression(max_iter=500).fit((X[tr] - X[tr].mean(0)) / (X[tr].std(0) + 1e-9), y[tr])
        p_gbm[te] = g.predict_proba(X[te])[:, 1]
        p_lr[te] = lr.predict_proba((X[te] - X[tr].mean(0)) / (X[tr].std(0) + 1e-9))[:, 1]
        # threshold = median prediction on the training set (take the better half)
        thr_g[a] = np.median(g.predict_proba(X[tr])[:, 1]); thr_l[a] = np.median(lr.predict_proba((X[tr] - X[tr].mean(0)) / (X[tr].std(0) + 1e-9))[:, 1])
        ev.loc[te, "tg"] = thr_g[a]; ev.loc[te, "tl"] = thr_l[a]
    y2 = ev.time >= months[0]
    base = ev.R[y2].values
    kg = y2 & (p_gbm >= ev.tg.values); kl = y2 & (p_lr >= ev.tl.values)
    print(f"\n### {key} exit={cfg}")
    print("   all signals (Y2)  :", s(base))
    print("   ML filter  LightGBM:", s(ev.R[kg].values))
    print("   ML filter  Logistic:", s(ev.R[kl].values))
    if key == ("5min","pullback") and cfg == (2.0,"tr6"):
        g = lgb.LGBMClassifier(n_estimators=150, num_leaves=7, min_child_samples=25, learning_rate=0.03, verbose=-1).fit(X[~y2.values], y[~y2.values])
        print("   feature importance:", dict(zip(FEAT, g.feature_importances_)))
