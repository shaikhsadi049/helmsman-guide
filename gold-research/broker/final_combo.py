"""Final package on both price sources: today vs consensus vs +H4-ER30 half-lot vs +inverse-vol slot weights (reduce-only)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "dk/lab"); import lab as LB
import prules as PR, rangefeat as RF
src = open("slotw.py").read().replace("w[m] = np.clip(ws[s] / mean, 0.25, 2.0)", "w[m] = np.clip(ws[s] / mean, 0.25, 1.0)"); SW = {}; exec(src, SW)
m = pd.read_parquet("dk/m1_bid.parquet"); H4 = m.resample("4h").agg({"close": "last"}).dropna().close
er = ((H4 - H4.shift(30)).abs() / H4.diff().abs().rolling(30).sum()).shift(1)   # last CLOSED H4 bar
def er_at(t):
    j = np.searchsorted(er.index.values, pd.DatetimeIndex(t).floor("4h").values, side="right") - 1; return er.values[np.clip(j, 0, len(er) - 1)]
TEND = pd.Timestamp("2026-08-01", tz="UTC")
def er_half(tr):
    rk = RF.past_rank_seq(er_at(tr.t.values), tr.slot.values); bad = tr.slot.str.startswith("S").values & np.isfinite(rk) & (rk > 0.8)
    d = tr.copy(); d.loc[bad, "R"] *= 0.5; return d
out = []; curves = {}
for name, f, today in (("broker", "dk/of/cons_trades_broker.parquet", None), ("COMEX", "of/cons_trades_comex.parquet", None)):
    tr = pd.read_parquet(f).sort_values("t").reset_index(drop=True)
    variants = {"consensus": tr, "+ER30½": er_half(tr)}
    variants["+ER30½ +invvol"] = SW["weights"](variants["+ER30½"], "invvol", 6)
    for v, d in variants.items():
        r = PR.rep(d, LB, LB.D0, TEND); r["calmar"] = round(r["sumR"] / r["DD"], 1); out.append(dict(data=name, variant=v, **r))
        dd = d[(d.t >= LB.D0) & (d.t < TEND)].sort_values("t"); curves[(name, v)] = (dd.t.values, dd.R.cumsum().values / dd.R.sum())
T = pd.DataFrame(out); print(T.to_string()); T.to_csv("final_combo.csv", index=False)
import pickle; pickle.dump(curves, open("final_curves.pkl", "wb"))
