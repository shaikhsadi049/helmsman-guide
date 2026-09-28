import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import adv_run as AR, adv as A, adv2, gcdata as G_
exec(open("adv_port_run.py").read().split("T = {}")[0].split("from adv_port import")[0])
from adv_port import ES, SPLIT
df = pd.read_parquet("adv_results.parquet")
exec("\n".join(l for l in open("adv_port_run.py").read().split("\n") if l.startswith(("def es_id","    return ES.index","def row","    q = df","    for k, v","        q = q[","    assert","    return q.iloc"))))
exec(open("adv_port_run.py").read().split("PICKS = ")[1].split("}\n")[0].join(["PICKS = ", "}\n"]))
TFMIN = {"5min": 5, "15min": 15, "1h": 60}
def run(r, ts_bars, ts_r):
    tf, entry, pb, conf, ar, sess = ES[int(r.es)]
    E = AR.entry_set(tf, entry, pb, conf, ar, sess)
    o = np.argsort(E["m1"], kind="stable")
    for k in E: E[k] = E[k][o]
    risk = E["atr"] * r.k * ((0.7 + 0.6 * E["volp"]) if r.adapt else 1.0)
    G = AR.GR[tf]; T = G if r.ttf == "same" else AR.GR[r.ttf]
    res = adv2.sim_ts(E["m1"].astype(np.int64), E["dir"].astype(np.int64), E["lvl"], risk, G.o, G.h, G.l, G.c, T.mgmt, T.atr1,
                      T.trend_up, T.trend_dn, r.r1, r.f1, r.lock, r.trail, bool(r.brk), r.gb_a, r.gb_g, G_.COST_RT, 60 * 24 * 15, ts_bars, ts_r)
    take = A.greedy(E["m1"], res[:, 2].astype(np.int64))
    t = AR.m1.index[E["m1"][take]]; R = res[take, 0]
    return R[t < SPLIT], R[t >= SPLIT]
def s(R):
    w = R > 0; return f"n={len(R):3d} win={w.mean()*100:3.0f}% PF={R[w].sum()/-R[~w].sum():.2f} R={R.sum():+6.1f}"
for name, r in PICKS.items():
    tf = ES[int(r.es)][0]
    base = run(r, 0, 0.0)
    best = None
    rows = []
    for nb in (2, 4, 8, 16):
        for tr_ in (0.1, 0.25, 0.5):
            a, b = run(r, nb * TFMIN[tf], tr_)
            rows.append((a.sum(), nb, tr_, a, b))
    rows.sort(key=lambda x: -x[0])
    _, nb, tr_, a, b = rows[0]
    print(f"{name}\n   no time-stop       Y1 {s(base[0])} | Y2 {s(base[1])}\n   best on Y1: {nb:2d} bars <{tr_}R  Y1 {s(a)} | Y2 {s(b)}")
