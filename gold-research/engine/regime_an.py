import pickle, numpy as np, pandas as pd
pd.set_option("display.width", 250)
data = pickle.load(open("regime_sims.pkl", "rb"))
SPLIT = pd.Timestamp("2025-08-01", tz="UTC")
def cells(ev):
    t = pd.cut(ev.adx, [-1, 20, 30, 999], labels=["weakT", "midT", "strongT"]).astype(str)
    v = pd.cut(ev.volp.fillna(.5), [-1, .33, .67, 2], labels=["calm", "normV", "wild"]).astype(str)
    return (t + "/" + v).values
for key in [("5min","pullback"), ("5min","swing"), ("15min","pullback"), ("15min","swing"), ("1h","pullback")]:
    ev, sims = data[key]
    keys = list(sims.keys())
    Rm = np.column_stack([sims[k][:, 0] for k in keys])          # trades x configs
    y1 = (ev.time < SPLIT).values; y2 = ~y1
    cell = cells(ev)
    # static: best single config on year1
    s_best = np.nanargmax(np.nanmean(Rm[y1], 0))
    static_y2 = Rm[y2, s_best]
    # adaptive: per-regime best on year1 (skip regime if its best mean <= 0.05R or <15 samples)
    adapt = np.full(len(ev), np.nan); choice = {}
    for c in np.unique(cell):
        m1 = y1 & (cell == c)
        if m1.sum() < 15:
            choice[c] = ("static", keys[s_best]); j = s_best
        else:
            mu = np.nanmean(Rm[m1], 0); j = int(np.nanargmax(mu))
            if mu[j] <= 0.05:
                choice[c] = ("SKIP", round(float(mu[j]), 2)); continue
            choice[c] = (keys[j], round(float(mu[j]), 2), int(m1.sum()))
        adapt[cell == c] = Rm[cell == c, j]
    a2 = adapt[y2]; a2n = a2[~np.isnan(a2)]
    def s(x):
        x = x[~np.isnan(x)]
        if len(x) == 0: return "none"
        pf = x[x > 0].sum() / -x[x <= 0].sum() if (x <= 0).any() else 99
        eq = np.cumsum(x); dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
        return f"n={len(x)} win={np.mean(x>0)*100:.0f}% PF={pf:.2f} exp={x.mean():+.3f}R tot={x.sum():+.1f}R DD={dd:.1f}R"
    print(f"\n######## {key}  entries={len(ev)} (y1={y1.sum()}, y2={y2.sum()})")
    print("  static best on Y1:", keys[s_best], "| Y1:", s(Rm[y1, s_best]), "\n                      Y2 (unseen):", s(static_y2))
    print("  ADAPTIVE Y2 (unseen):", s(a2))
    for c, ch in sorted(choice.items()): print("     ", c, "->", ch)
