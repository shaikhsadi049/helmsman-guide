from common import *
for EX in [144, BASE]:
    y=R4[:,EX]; kn=X4[:,EX]; print(pstr(EX), short(M(EX)))
    for N in [10,20,40]:
        for thr in [0.0,-0.1]:
            take=np.ones(len(rows),bool)
            for i in range(len(rows)):
                past=np.where(kn<m1[i])[0][-N:]
                if len(past)==N and y[past].mean()<thr: take[i]=False
            m=M(EX,take); print(f"  eqfilter N={N} thr={thr} skip={100*(1-take[IN].mean()):.0f}%", short(m))
