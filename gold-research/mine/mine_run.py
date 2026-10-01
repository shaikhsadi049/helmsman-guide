import sys, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/mine")
import engine as E, rules as RL
tf = sys.argv[1]; T = E.TF(tf); G = RL.gates(T); rows = []; t0 = time.time(); k = 0
for fam, name, formula, Lf, Sf in RL.generate(T):
    L0 = T.cut(np.nan_to_num(Lf).astype(float)) > 0; S0 = T.cut(np.nan_to_num(Sf).astype(float)) > 0
    for g, (gl, gs) in G.items():
        L = L0 & gl; S = S0 & gs
        for r in E.evaluate(T, L, S, min_n=40):
            rows.append(dict(tf=tf, family=fam, rule=name, gate=g, formula=formula, **r))
        k += 1
    if k % 200 == 0: print(tf, k, "rules x gates", round(time.time() - t0), "s", flush=True)
df = pd.DataFrame(rows); df.to_parquet(f"mined_{tf}.parquet"); print(tf, "done", len(df), "rows", round(time.time() - t0), "s")
