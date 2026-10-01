"""Survivors of the mine: strict filters, robustness across exits, random-entry null WITHIN the same gate, direction balance."""
import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/mine")
import engine as E, rules as RL
df = pd.concat([pd.read_parquet(f"mined_{tf}.parquet") for tf in ("5min", "15min", "1h")], ignore_index=True)
print("evaluations:", len(df), "| rule x gate combos:", df.groupby(["tf", "rule", "gate"]).ngroups)
key = ["tf", "family", "rule", "gate"]
# robustness across the 48 exits: share of exits with sumR>0 and >=5/7 quarters positive
rob = df.groupby(key).apply(lambda g: pd.Series(dict(n_exits=len(g), share_pos=((g.sumR > 0) & (g.qpos >= 5)).mean(), med_score=g.score.median())))
best = df.sort_values("score").groupby(key).tail(1).set_index(key).join(rob)
cand = best[(best.n >= 60) & (best.qpos >= 6) & (best.mpos >= 13) & (best.PF >= 1.25) & (best.share_pos >= 0.6) & (best.short_R > 0) & (best.long_R > 0)]
print("pass strict filters (incl. both directions profitable, 60%+ of exits robust):", len(cand))
cand = cand.sort_values("score", ascending=False).head(250).reset_index()
# null within the gate
Ts = {tf: E.TF(tf) for tf in cand.tf.unique()}; Gs = {tf: RL.gates(Ts[tf]) for tf in Ts}
gen_cache = {}
def masks(tf, rule):
    if (tf, rule) not in gen_cache:
        for fam, name, formula, Lf, Sf in RL.generate(Ts[tf]):
            gen_cache[(tf, name)] = (Ts[tf].cut(np.nan_to_num(Lf).astype(float)) > 0, Ts[tf].cut(np.nan_to_num(Sf).astype(float)) > 0)
    return gen_cache[(tf, rule)]
def null_gate(T, gl, gs, nl, ns, j, draws, rng):
    al, as_ = np.where(gl & T.live)[0], np.where(gs & T.live)[0]; out = []
    m1i = T.B.m1.values.astype(np.int64); Rm = np.asarray(T.R); Xm = np.asarray(T.X)
    for _ in range(draws):
        bl = rng.choice(al, min(nl, len(al)), replace=False); bs = rng.choice(as_, min(ns, len(as_)), replace=False)
        bb = np.r_[bl, bs]; dd = np.r_[np.ones(len(bl), np.int64), -np.ones(len(bs), np.int64)]; o = np.argsort(bb)
        r, _, _ = E.greedy_m1(bb[o], dd[o], m1i, Xm, Rm, j, T.live)
        eq = np.cumsum(r); ddv = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max() if len(r) else 0
        out.append(r.sum() / max(ddv, 1))
    return np.array(out)
rng = np.random.default_rng(1); pv = []; nmed = []
for i, row in cand.iterrows():
    T = Ts[row.tf]; L0, S0 = masks(row.tf, row.rule); gl, gs = Gs[row.tf][row.gate]
    L, S = L0 & gl & T.live, S0 & gs & T.live
    nd = null_gate(T, gl, gs, L.sum(), S.sum(), int(row.exit), 300, rng)
    pv.append((nd >= row.score).mean()); nmed.append(np.median(nd))
cand["null_p"] = pv; cand["null_med_score"] = nmed
# multiple testing: ~N tested combos; Bonferroni-like bar = p < 1/300 (no null draw beat it)
cand["survives_null"] = cand.null_p == 0
cand.to_parquet("survivors.parquet")
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 40)
cols = ["tf", "family", "rule", "gate", "exit", "n", "PF", "sumR", "maxDD", "score", "mpos", "qpos", "eqR2", "top5", "long_R", "short_R", "share_pos", "null_med_score", "null_p"]
print(cand[cols].round(2).head(60).to_string())
print("\nsurvive null (0 of 300 random beat them):", cand.survives_null.sum())
print(cand[cand.survives_null].groupby(["tf", "family"]).size())
