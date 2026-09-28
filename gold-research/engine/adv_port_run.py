import numpy as np, pandas as pd
from adv_port import trades, summary, ES, SPLIT
df = pd.read_parquet("adv_results.parquet")
df["tf"] = [ES[i][0] for i in df.es]
def es_id(tf, entry, pb, conf, adx, sess):
    return ES.index((tf, entry, pb, conf, adx, sess))
def row(**kw):
    q = df
    for k, v in kw.items():
        q = q[np.isclose(q[k], v)] if isinstance(v, float) else q[q[k] == v]
    assert len(q) == 1, (kw, len(q))
    return q.iloc[0]
PICKS = {
 "S1 15m swing  | TP1 0.5R, runner->4H trend": row(es=es_id("15min","swing",30,(),"any",(7,20)), k=0.75, adapt=True, r1=0.5, f1=0.5, lock=0.0, ttf="4h", trail=0.0, brk=True, gb_a=0.0),
 "S2 15m pullb+1H conf | runner->4H": row(es=es_id("15min","pullback",40,("1h",),"lt30",(7,20)), k=0.75, adapt=True, r1=0.5, f1=0.5, lock=0.25, ttf="4h", trail=0.0, brk=True, gb_a=0.0),
 "S3 5m pullb+15m conf | runner->4H": row(es=es_id("5min","pullback",30,("15min",),"any",None), k=3.0, adapt=True, r1=0.5, f1=0.5, lock=0.0, ttf="4h", trail=0.0, brk=True, gb_a=0.0),
 "S4 1h pullback | TP1 .75R, trail 3ATR": row(es=es_id("1h","pullback",30,(),"lt30",(7,20)), k=1.0, adapt=False, r1=0.75, f1=0.5, lock=0.25, ttf="1h", trail=3.0, brk=False, gb_a=2.0),
 "R1 5m pullb+15m pure RUNNER (4H)": row(es=es_id("5min","pullback",40,("15min",),"lt30",None), k=1.5, adapt=True, r1=0.0, f1=0.0, lock=0.0, ttf="4h", trail=0.0, brk=True, gb_a=0.0),
}
T = {}
for name, r in PICKS.items():
    T[name] = trades(r); summary(T[name], name)
def combo(names, label):
    t = pd.concat([T[n].assign(s=n) for n in names]).sort_values("t_out").reset_index(drop=True)
    summary(t, f"\n>>> PORTFOLIO {label}: " + " + ".join(n.split()[0] for n in names))
    # worst simultaneous exposure
    ev = pd.concat([pd.DataFrame({"t": t.t_in, "d": 1}), pd.DataFrame({"t": t.t_out, "d": -1})]).sort_values("t")
    print("   max simultaneous open trades:", ev.d.cumsum().max())
    return t
P1 = combo(["S1 15m swing  | TP1 0.5R, runner->4H trend", "S2 15m pullb+1H conf | runner->4H", "S3 5m pullb+15m conf | runner->4H", "S4 1h pullback | TP1 .75R, trail 3ATR"], "HIGH-WIN multi-TF")
P2 = combo(list(PICKS), "HIGH-WIN + pure runner")
P1.to_csv("portfolio_highwin_trades.csv", index=False); P2.to_csv("portfolio_all_trades.csv", index=False)
