import pickle, numpy as np, pandas as pd
pd.set_option("display.width", 250)
data = pickle.load(open("regime_sims.pkl", "rb"))
for key in [("5min","pullback"), ("15min","pullback"), ("1h","pullback")]:
    ev, sims = data[key]
    vol = pd.cut(ev.volp.fillna(.5), [-1, .33, .67, 2], labels=["calm", "normal", "wild"]).astype(str).values
    tr = pd.cut(ev.adx, [-1, 20, 30, 999], labels=["weak", "mid", "strong"]).astype(str).values
    print(f"\n##### {key}: mean R per trade by trailing width (ATR multiples), SL=1.5 ATR; rows = market state")
    rows = []
    for dim, lab in (("vol", vol), ("trend", tr)):
        for g in np.unique(lab):
            m = lab == g
            row = {"state": f"{dim}:{g}", "n": int(m.sum())}
            for t in ("tr1.5", "tr2", "tr3", "tr4", "tr6", "brk", "tp2", "tp3"):
                row[t] = np.nanmean(sims[(1.5, t)][m, 0])
            best = max(("tr1.5","tr2","tr3","tr4","tr6","brk"), key=lambda k: row[k]); row["best"] = best
            mfe = sims[(1.5, "tr6")][m, 1]
            row["medMFE"] = np.median(mfe)
            rows.append(row)
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    # giveback: of trades that reached >= 3R, how much of the peak each trail keeps
    m = sims[(1.5, "tr6")][:, 1] >= 3
    print(f"   trades reaching 3R+: {m.sum()} | kept share of peak (R_final / MFE):",
          {t: round(float(np.nanmedian(sims[(1.5, t)][m, 0] / sims[(1.5, t)][m, 1])), 2) for t in ("tr1.5","tr2","tr3","tr4","tr6","brk")})
