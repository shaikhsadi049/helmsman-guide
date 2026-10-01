exec(open("eqfilter.py").read().split("rows = []")[0])
df = pd.concat([taken(s, sp, a).assign(R=lambda x, w=w: x.R * w) for s, sp, w, a in CONS]).sort_values("t")
df = df[(df.t >= D0) & (df.t < TEND)]; eq = df.R.cumsum().values; pk = np.maximum.accumulate(eq); j = (pk - eq).argmax(); i = (eq[:j] == pk[j]).nonzero()[0][-1]
t0, t1 = df.t.iloc[i], df.t.iloc[j]; print("DD", round(pk[j]-eq[j],1), t0, "->", t1)
w = df[(df.t > t0) & (df.t <= t1)]; print(w.groupby("slot").R.agg(["sum", "count"]).round(1))
mo = df.groupby([df.t.dt.tz_localize(None).dt.to_period("M"), "slot"]).R.sum().unstack().round(1); print(mo.to_string())
