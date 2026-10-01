import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../..")
exec(open("eqfilter.py").read().split("rows = []")[0])
import prules as PR
idx = pd.DatetimeIndex(pd.read_parquet("../m1_bid.parquet", columns=["close"]).index)
def taken3(slot, spec, adx):
    r = OUT[slot]; rows = r["rows"]; R, X = r[spec]; ok = np.isfinite(R); rr = rows[ok]; t = lab.greedy(rr, X[ok])
    w = np.where(r["adx_bad"][ok][t], 0.5, 1.0) if adx else np.ones(t.sum())
    return pd.DataFrame(dict(t=lab.TIME[rr[t]], tx=idx[np.clip(X[ok][t], 0, len(idx) - 1)], R=R[ok][t] * w, slot=slot, dir=SIG.dir.values[rr[t]]))
tr = pd.concat([taken3(s, sp, a).assign(R=lambda x, w=w: x.R * w) for s, sp, w, a in CONS], ignore_index=True)
tr.to_parquet("cons_trades_broker.parquet")
PR.run_all(tr, lab, D0, TEND).to_csv("prules_broker.csv", index=False)
