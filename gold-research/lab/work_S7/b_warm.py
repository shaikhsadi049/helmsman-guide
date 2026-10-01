from common import *
ms=np.load("ms.npy")
W=~IN
def wmet(j):
    idx=np.where(W)[0]; Rv=R7[idx,j]; Xv=X7[idx,j]; out=[]; free=-1
    for k,i in enumerate(idx):
        if free<M[i] and Xv[k]<ms[0]: out.append(k); free=Xv[k]
        elif free<M[i]: free=Xv[k]
    return lab.metrics(Rv[out].astype(float),T[idx[out]])
for s in ("k50","k70"):
  for p in ("slot","none"):
    for r in ("none","q90k50","2R_k50"):
      for be in ("none","be1"):
        j=pidx(sq=s,tp="none",part=p,be=be,trail="h4q80",rat=r,ts="none")[0]
        m=wmet(j); print(f"{pname(j):40s}",{k:m[k] for k in ("n","PF","sumR","maxDD_R","months_pos","eq_R2","top5days_pct")})
