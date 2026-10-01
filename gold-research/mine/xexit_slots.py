import sys, numpy as np, pandas as pd, pickle, time, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "../lab")
import xexit as XE, lab
SIG = lab.SIG; rows_all = []; t0 = time.time()
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
for slot in ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
    rows = np.where(SIG.slot.values == slot)[0]; s = SIG.iloc[rows]; tf = s.tf.iloc[0]
    k = np.clip(s[SQ[slot]].values, 0.5, 8.0); risk = k * s.atr.values; hor = np.full(len(rows), 60 * 24 * 10)
    for j, ex in enumerate(XE.exit_menu(tf)):
        R, X = XE.run(s.m1.values, s.dir.values, s.lvl.values, risk, hor, tp=ex["tp"], be=ex["be"], trail=ex["trail"], stall=ex.get("stall", 0),
                      prog=ex.get("prog", (0, 0.0)), gb=ex.get("gb", (0, 0.0)), tf_flag=tf)
        live = (lab.TIME[rows] >= lab.D0); rr = rows[live]; Rl = np.asarray(R)[live]; Xl = np.asarray(X)[live]
        tk = lab.greedy(rr, Xl); m = lab.metrics(Rl[tk], lab.TIME[rr[tk]])
        rows_all.append(dict(slot=slot, j=j, desc=XE.describe(ex), **m))
    print(slot, round(time.time() - t0), "s", flush=True)
df = pd.DataFrame(rows_all); df.to_parquet("xexit_slots.parquet")
