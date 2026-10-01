from h import *
import time; t0=time.time()
idx = np.where(in25)[0]; q = T[idx].tz_localize(None).to_period("Q")
rows_out=[]
for j in TREND:
    r = R1[idx, j]
    qm = pd.Series(r).groupby(q.values).mean()
    i, rg = run(j); m = lab.metrics(rg, T[i])
    rows_out.append(dict(j=j, sig_mean=r.mean(), sig_med=np.median(r), sig_q_pos=(qm>0).sum(), sig_sum=r.sum(), **{k:m[k] for k in K if k!="top5days_pct"}, top5=m["top5days_pct"]))
D = pd.DataFrame(rows_out)
for c in ["sq","tp","part","be","trail","rat","ts"]: D[c]=[P[j][c] for j in D.j]
D.to_parquet("B_all.parquet"); print(time.time()-t0)
