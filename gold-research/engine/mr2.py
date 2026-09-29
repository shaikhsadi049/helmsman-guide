import numpy as np, pandas as pd, itertools, pickle, warnings; warnings.filterwarnings("ignore")
import mr as M, dyn2_run as R2
base_entries = M.entries
H1 = R2.GR["1h"]
def entries2(tf, fam, regime, sess):
    reg0 = "no4h" if regime.startswith("no4h") else regime
    E = base_entries(tf, fam, reg0, sess)
    mi = E["m1"]
    if regime == "no4h+no1h": k = ~H1.trend_up[mi] & ~H1.trend_dn[mi]
    elif regime == "no4h+dweak": k = M.dt_at(mi) < 0.5
    elif regime == "no4h+dstrong": k = M.dt_at(mi) >= 0.5
    else: k = np.ones(len(mi), bool)
    return {kk: (v[k] if isinstance(v, np.ndarray) and len(v) == len(mi) else v) for kk, v in E.items()}
M.entries = entries2
T = pd.read_parquet("../trades_v3_reg.parquet"); T = T[T.slot != 6]
keep = np.zeros(len(T), bool); bu = {}
for i, (s, a, b) in enumerate(zip(T.slot, T.t_in, T.t_out)):
    if bu.get(s, -1) < a: keep[i] = True; bu[s] = b
X = T[keep]; TM = X.groupby(X.time.dt.tz_localize(None).dt.to_period("M")).R.sum(); flat = TM.index[TM < 10]
rows = []; keepT = {}
base_h = dict(M.MRH)
for tf, fam in [("15min", "rsi2"), ("1h", "z2"), ("30min", "z2.5"), ("30min", "ext3"), ("1h", "fbo"), ("15min", "ext3"), ("30min", "fbo")]:
    for regime, sess, hm, qsl, qtp in itertools.product(["no4h", "no4h+no1h", "no4h+dweak", "no4h+dstrong"], [False, True], [0.5, 1, 2], [0.7, 0.9], [0.3, 0.5, 0.7]):
        M.MRH[tf] = int(base_h[tf] * hm)
        r = M.run(tf, fam, regime, sess, qsl, qtp)
        M.MRH[tf] = base_h[tf]
        if r is None or len(r) < 30: continue
        R = r.R.values; w = R > 0; Rc = R - 1.66 / r.risk.values
        mo = r.groupby(r.time.dt.tz_localize(None).dt.to_period("M")).R.sum().reindex(TM.index, fill_value=0)
        q = r.groupby(r.time.dt.tz_localize(None).dt.to_period("Q")).R.sum()
        key = (tf, fam, regime, sess, hm, qsl, qtp); keepT[key] = r
        rows.append(dict(tf=tf, fam=fam, regime=regime, sess=sess, hm=hm, qsl=qsl, qtp=qtp, n=len(R), win=w.mean(), PF=R[w].sum() / max(1e-9, -R[~w].sum()),
                         sumR=R.sum(), qpos=(q > 0).sum(), cost2=Rc.sum(), corr=np.corrcoef(mo.values, TM.values)[0, 1], flatR=mo.reindex(flat).sum()))
df = pd.DataFrame(rows); df.to_parquet("../mr2_grid.parquet"); pickle.dump(keepT, open("../mr2_trades.pkl", "wb"))
pd.set_option("display.width", 250)
g = df.groupby(["tf", "fam", "regime", "sess"]).agg(cfg=("sumR", "size"), prof=("sumR", lambda s: (s > 0).mean()), cost2prof=("cost2", lambda s: (s > 0).mean()),
    PF=("PF", "median"), sumR=("sumR", "median"), n=("n", "median"), qpos=("qpos", "median"), flatR=("flatR", "median"), corr=("corr", "median")).round(2)
print(g.sort_values("sumR", ascending=False).to_string())
