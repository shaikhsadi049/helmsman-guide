"""For every rule x gate x exit: monthly R from 2024-06 (warm-up included) -> causal online selection test."""
import sys, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/mine")
import engine as E, rules as RL
tf = sys.argv[1]; T = E.TF(tf); G = RL.gates(T)
T.live = np.ones(len(T.B), bool)                      # include warm-up months
months = sorted(pd.unique(T.month)); mi = {m: i for i, m in enumerate(months)}; mon_idx = np.array([mi[m] for m in T.month])
m1i = T.B.m1.values.astype(np.int64); Rm = np.asarray(T.R); Xm = np.asarray(T.X)
names = []; mats = []; t0 = time.time()
for fam, name, formula, Lf, Sf in RL.generate(T):
    L0 = T.cut(np.nan_to_num(Lf).astype(float)) > 0; S0 = T.cut(np.nan_to_num(Sf).astype(float)) > 0
    for g, (gl, gs) in G.items():
        b, d = E.masks_to_signals(L0 & gl, S0 & gs)
        if len(b) < 30: continue
        M = np.zeros((len(E.EXITS), len(months), 2), np.float32)    # [exit, month, (sumR, nTrades)]
        for j in range(len(E.EXITS)):
            r, bb, dd = E.greedy_m1(b, d, m1i, Xm, Rm, j, T.live)
            np.add.at(M[j, :, 0], mon_idx[bb], r); np.add.at(M[j, :, 1], mon_idx[bb], 1)
        names.append((tf, fam, name, g, formula)); mats.append(M)
np.save(f"monthly_{tf}.npy", np.stack(mats)); pd.DataFrame(names, columns=["tf", "family", "rule", "gate", "formula"]).to_parquet(f"monthly_{tf}_names.parquet")
pd.Series(months).to_csv(f"months_{tf}.csv", index=False); print(tf, "done", len(names), round(time.time() - t0), "s")
