import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, pickle
src = open("combo_sim.py").read().split('if __name__ == "__main__":')
exec(src[0].replace("rp = mn + (mx - mn) * xdd * tr", "rp = (mn + (mx - mn) * xdd * tr) * (0.5 if MRk[i] else 1.0)"))
RT = pickle.load(open("../ratchet_T.pkl", "rb"))
FADE = pd.read_parquet("../combo_trades_tick.parquet"); FADE = FADE[FADE.kind == "mr"]
def run(name, T, mx):
    df = pd.concat([T[FADE.columns.intersection(T.columns)], FADE]).sort_values("t_in").reset_index(drop=True); P = prep(df)
    R0 = df.R.values; Rw = np.where(R0 > 0, R0 * .5, R0)
    a = sim(df, R0, mx=mx, P=P); b = sim(df, Rw, mx=mx, P=P)
    cv = pd.DataFrame(a[3], columns=["i", "eq"]); cv["d"] = df.time.dt.tz_localize(None).dt.floor("D").values[cv.i.values]
    de = cv.groupby("d").eq.last(); dret = np.log(de).diff().fillna(np.log(de.iloc[0]))
    top5 = dret.nlargest(5).sum() / dret.sum() * 100
    me = cv.assign(m=pd.DatetimeIndex(cv.d).to_period("M")).groupby("m").eq.last(); mr = me.pct_change().fillna(me.iloc[0] - 1)
    print(f"{name:26s} max{mx} | full {a[0]*100:+8,.0f}% DD {a[1]*100:2.0f}% | weak {b[0]*100:+5,.0f}% DD {b[1]*100:2.0f}% | top-5 days = {top5:3.0f}% of growth | losing months {(mr<0).sum()}/{len(mr)} | median month {mr.median()*100:+.1f}%", flush=True)
for mx in (5, 3, 2):
    for key, nm in [((None, 0), "no ratchet (Assay now)"), ((0.8, 0.3), "ratchet q0.8 lock30%"), ((0.8, 0.5), "ratchet q0.8 lock50%"), ((0.9, 0.5), "ratchet q0.9 lock50%")]:
        run(nm, RT[key], mx)
