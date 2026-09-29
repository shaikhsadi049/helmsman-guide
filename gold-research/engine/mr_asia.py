import numpy as np, pandas as pd, itertools, warnings; warnings.filterwarnings("ignore")
import mr as M, dyn2_run as R2
orig = M.entries
def entries_s(tf, fam, regime, sess):
    if sess in (True, False): return orig(tf, fam, regime, sess)
    E = orig(tf, fam, regime, False)
    h = pd.DatetimeIndex(R2.idx[E["m1"]]).hour.values
    k = (h >= 0) & (h < 7) if sess == "asia" else (h >= 20) | (h < 7) if sess == "night" else (h >= 12) & (h < 17)
    return {kk: (v[k] if isinstance(v, np.ndarray) and len(v) == len(k) else v) for kk, v in E.items()}
M.entries = entries_s
rows = []
for tf, fam, regime, sess, qsl, qtp in itertools.product(["5min", "15min", "30min"], ["rsi2", "z2", "z2.5", "fbo", "ext3"], ["none", "no4h"], ["asia", "night"], [0.7, 0.9], [0.3, 0.5, 0.7]):
    r = M.run(tf, fam, regime, sess, qsl, qtp)
    if r is None or len(r) < 30: continue
    R = r.R.values; w = R > 0; q = r.groupby(r.time.dt.tz_localize(None).dt.to_period("Q")).R.sum(); Rc = R - 1.66 / r.risk.values
    rows.append(dict(tf=tf, fam=fam, regime=regime, sess=sess, qsl=qsl, qtp=qtp, n=len(R), win=w.mean(), PF=R[w].sum() / max(1e-9, -R[~w].sum()), sumR=R.sum(), qpos=(q > 0).sum(), cost2=Rc.sum()))
df = pd.DataFrame(rows); df.to_parquet("../mr_asia.parquet")
pd.set_option("display.width", 250)
g = df.groupby(["tf", "fam", "regime", "sess"]).agg(cfg=("sumR", "size"), prof=("sumR", lambda s: (s > 0).mean()), cost2prof=("cost2", lambda s: (s > 0).mean()),
    PF=("PF", "median"), sumR=("sumR", "median"), n=("n", "median"), qpos=("qpos", "median")).round(2)
print(g.sort_values("sumR", ascending=False).head(25).to_string())
print("\noverall share profitable:", round((df.sumR > 0).mean(), 2), "| by sess:", df.groupby("sess").sumR.apply(lambda s: round((s > 0).mean(), 2)).to_dict())
