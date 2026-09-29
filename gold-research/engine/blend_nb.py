exec(open("blend.py").read().split('rowb("fixed 2%"')[0])
for N in (100, 200, 300, 500):
    for kf in (0.25, 0.5, 1.0):
        rowb(f"(tr+k)xdd N{N} kf{kf}", w_dd=0, w_tr=1, w_k=1, N=N, kfrac=kf)
for fdd in (0.15, 0.25):
    rowb(f"(tr+k)xdd fullDD{fdd}", w_dd=0, w_tr=1, w_k=1, fdd=fdd)
