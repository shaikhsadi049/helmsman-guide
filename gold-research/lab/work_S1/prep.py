import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd, time
t=time.time()
ms = lab.month_starts_m1(); np.save("ms.npy", ms)
rows = np.where(lab.SIG.slot.values=="S1")[0]
np.save("rows.npy", rows)
R_=lab.load_R(); X_=lab.load_X(); MF=lab.load_MF()
np.save("R1.npy", np.asarray(R_[rows])); np.save("X1.npy", np.asarray(X_[rows])); np.save("MF1.npy", np.asarray(MF[rows]))
print(time.time()-t, len(rows), (lab.TIME[rows]>=lab.D0).sum(), lab.baseline_policy("S1"))
print(lab.SIG.slot.value_counts())
print(lab.SIG.iloc[rows].head())
