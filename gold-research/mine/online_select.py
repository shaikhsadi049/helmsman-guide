"""Honest test of rule mining as a PROCESS: at each month start choose the top-K rules (rule x gate x exit) using ONLY
past months (2024-06 .. last month), trade them next month (equal risk each). No look at the future."""
import numpy as np, pandas as pd
mats, names = [], []
for tf in ("5min", "15min", "1h"):
    M = np.load(f"monthly_{tf}.npy"); N = pd.read_parquet(f"monthly_{tf}_names.parquet")
    months = pd.read_csv(f"months_{tf}.csv").iloc[:, 0].tolist(); mats.append(M); names.append(N)
M = np.concatenate(mats); N = pd.concat(names, ignore_index=True)       # [combo, exit, month, (R, n)]
months = months; t25 = months.index("2025-01")
C, X, TT, _ = M.shape; print("combos", C, "exits", X, "months", TT, months[0], "..", months[-1])
R = M[..., 0].reshape(C * X, TT); Nn = M[..., 1].reshape(C * X, TT)
combo_of = np.repeat(np.arange(C), X); exit_of = np.tile(np.arange(X), C)
rulekey = (N.tf + "|" + N.rule).values[combo_of]
def past_stats(t, window):
    a = 0 if window is None else max(0, t - window)
    r = R[:, a:t]; n = Nn[:, a:t].sum(1); eq = np.cumsum(r, 1)
    dd = (np.maximum.accumulate(np.concatenate([np.zeros((len(r), 1)), eq], 1), 1)[:, 1:] - eq).max(1)
    return r.sum(1), dd, n, (r > 0).mean(1)
def run(K, window, min_n=20, score="ret_dd", one_per_rule=True, seed=None):
    out = []; rng = np.random.default_rng(seed) if seed is not None else None
    for t in range(t25, TT):
        s, dd, n, pos = past_stats(t, window)
        ok = n >= min_n
        sc = np.where(ok, s / np.maximum(dd, 1.0) if score == "ret_dd" else s, -np.inf)
        if rng is not None:
            cand = np.where(ok)[0]; pick = rng.choice(cand, K, replace=False)
        else:
            order = np.argsort(-sc); pick = []; seen = set()
            for i in order:
                if not np.isfinite(sc[i]): break
                if one_per_rule and rulekey[i] in seen: continue
                pick.append(i); seen.add(rulekey[i])
                if len(pick) == K: break
            pick = np.array(pick)
        out.append(R[pick, t].mean())
    return np.array(out)
def rep(x, name):
    eq = np.cumsum(x); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    return f"{name:40s} sum {x.sum():+6.1f}R/rule | months+ {(x>0).sum()}/{len(x)} | worst month {x.min():+.2f} | maxDD {dd:.2f} | sum/DD {x.sum()/max(dd,1e-9):.1f}"
mo = months[t25:]
print("months:", mo[0], "..", mo[-1])
res = {}
for K in (5, 10, 20, 40):
    for window in (None, 6, 12):
        x = run(K, window); res[(K, window)] = x
        print(rep(x, f"top-{K} by past ret/DD, window={window or 'all'}"))
rnd = np.array([run(10, None, seed=s) for s in range(30)])
print(rep(rnd.mean(0), "random 10 eligible rules (avg of 30 draws)"))
print(rep(np.nanmean(R[:, t25:], 0), "average of ALL candidates"))
pd.DataFrame({f"K{K}_w{w or 'all'}": v for (K, w), v in res.items()}, index=mo).to_csv("online_select_monthly.csv")
# what did it pick most often (K=10, all history)?
cnt = {}
for t in range(t25, TT):
    s, dd, n, pos = past_stats(t, None); sc = np.where(n >= 20, s / np.maximum(dd, 1), -np.inf); order = np.argsort(-sc); seen = set(); k = 0
    for i in order:
        if rulekey[i] in seen: continue
        seen.add(rulekey[i]); key = (N.tf[combo_of[i]], N.family[combo_of[i]], N.rule[combo_of[i]], N.gate[combo_of[i]]); cnt[key] = cnt.get(key, 0) + 1; k += 1
        if k == 10: break
print(pd.Series(cnt).sort_values(ascending=False).head(20).to_string())
