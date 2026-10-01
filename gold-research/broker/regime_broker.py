import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../..")
exec(open("eqfilter.py").read().split("rows = []")[0])
import regime_common as RC
F = lab.load_F()
def taken2(slot, spec, adx):
    r = OUT[slot]; rows = r["rows"]; R, X = r[spec]; ok = np.isfinite(R); rr = rows[ok]; t = lab.greedy(rr, X[ok])
    w = np.where(r["adx_bad"][ok][t], 0.5, 1.0) if adx else np.ones(t.sum())
    return pd.DataFrame(dict(t=lab.TIME[rr[t]], R=R[ok][t] * w, slot=slot, row=rr[t]))
tr = pd.concat([taken2(s, sp, a).assign(R=lambda x, w=w: x.R * w) for s, sp, w, a in CONS], ignore_index=True)
res = RC.evaluate(tr, SIG, F, lab, D0, TEND); res.to_csv("regime_broker.csv", index=False); print(res.to_string())
