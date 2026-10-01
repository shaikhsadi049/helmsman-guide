import sys; sys.path.insert(0, ".."); import lab, numpy as np, pandas as pd
S=lab.SIG; R_=lab.load_R(); X_=lab.load_X()
r6=np.where(S.slot.values=="S6")[0]; r3=np.where(S.slot.values=="S3")[0]
i3=pd.Series(r3,index=S.m1.values[r3]); i3=i3[~i3.index.duplicated()]
mp=i3.loc[S.m1.values[r6]].values
A=np.asarray(R_[r6,:3600]); B=np.asarray(R_[mp,:3600])
print("dir equal",(S.dir.values[r6]==S.dir.values[mp]).mean(),"R identical frac", np.mean(np.isclose(A,B,equal_nan=True)))
print("atr eq",np.mean(np.isclose(S.atr.values[r6],S.atr.values[mp])))
x=np.asarray(X_[r6,1208]); m1=S.m1.values[r6]
print("holding minutes median/mean baseline (2025+):", np.median((x-m1)[lab.TIME[r6]>=lab.D0]), np.mean((x-m1)[lab.TIME[r6]>=lab.D0]))
print(S.columns.tolist())
