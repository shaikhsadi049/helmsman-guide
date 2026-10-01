"""Why does an empty slot not trade? For every slot: raw triggers -> each filter -> final signals; and how much of
2025+ time the slot sat FLAT, how many signals arrived while flat (taken) vs while busy (lost)."""
import sys; sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import v3_parity as V, dyn2_run as R2, strat as S, mr as M, lab
idx = R2.idx; t25 = idx >= lab.D0
def trig_trend(tf, fam):
    G = R2.GR[tf]; F = G.F; c = G.bars.close.values
    if fam.startswith("rsi2"):
        th = float(fam.split("_")[1]); r = V.mt5_rsi(c, 2); L = r < th; Sg = r > 100 - th
    elif fam == "brk20":
        hh = G.bars.high.rolling(20).max().shift(1).values; ll = G.bars.low.rolling(20).min().shift(1).values; L = c > hh; Sg = c < ll
    else:  # pullback: bar dips into EMA30 and closes back beyond it (stack checked separately)
        L, Sg = S.signals(F, "pullback", 0, (), None, 30); L = L.copy(); Sg = Sg.copy()
        # pullback signal already requires the stack; recompute without it is not available -> report from stack step
    return G, F, L, Sg
rows = []
for name, sl in zip(["S1", "S2", "S3", "S4", "S5", "S6", "S7"], V.SLOTS):
    tf, fam, nc, sess = sl[:4]
    G, F, L, Sg = trig_trend(tf, fam)
    in25 = idx[G.pos] >= lab.D0
    step = {}
    raw = (L | Sg) & in25; step["1 raw trigger"] = raw.sum()
    Ls, Ss = L & F.bull, Sg & F.bear; step["2 + TF 6-EMA stack"] = ((Ls | Ss) & in25).sum()
    hl, hs = S.filters(F, 0, ("4h", "1D"), None, 1), S.filters(F, 0, ("4h", "1D"), None, -1)
    Lh, Sh = Ls & hl, Ss & hs; step["3 + H4 & D1 EMA20/50"] = ((Lh | Sh) & in25).sum()
    mi = G.pos; Lc, Sc = Lh.copy(), Sh.copy()
    for ctf in R2.NEXT[tf][:nc]:
        H = R2.GR[ctf]; Lc &= H.trend_up[mi]; Sc &= H.trend_dn[mi]
    step["4 + higher-TF stack (CONF)"] = ((Lc | Sc) & in25).sum()
    if sess:
        h = F.hour; ok = (h >= 7) & (h < 20); Lc &= ok; Sc &= ok
    step["5 + session"] = ((Lc | Sc) & in25).sum()
    rows.append((name, tf, step))
for name, spec in [("F8", ("15min", "rsi2", "no4h", True)), ("F9", ("1h", "z2", "no4h", False)), ("F10", ("30min", "z2.5", "no4h", False)), ("F11", ("1h", "fbo", "no4h", True))]:
    tf = spec[0]; G = R2.GR[tf]; L, Sg = M.raw_signals(tf, spec[1]); in25 = idx[G.pos] >= lab.D0; step = {}
    step["1 raw trigger"] = ((L | Sg) & in25).sum()
    ok4 = ~R2.G4.trend_up[G.pos] & ~R2.G4.trend_dn[G.pos]; step["2 + H4 not trending"] = ((L | Sg) & in25 & ok4).sum()
    if spec[3]: h = G.F.hour; okS = (h >= 7) & (h < 20)
    else: okS = np.ones(len(L), bool)
    step["3 + session"] = ((L | Sg) & in25 & ok4 & okS).sum()
    rows.append((name, tf, step))
print("FILTER FUNNEL (2025-01..2026-07, number of bars that pass)")
for name, tf, st in rows:
    print(f"{name:4s} {tf:6s} " + " -> ".join(f"{k[2:]}: {v}" for k, v in st.items()))
# time flat vs busy, signals lost while busy (baseline exits)
print("\nSLOT OCCUPANCY (baseline Assay exits, one position per slot)")
X_ = lab.load_X(); tot_min = (idx >= lab.D0).sum()
for s in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "F8", "F9", "F10", "F11"]:
    rows_all = np.where((lab.SIG.slot.values == s) & (lab.TIME >= lab.D0))[0]
    rr, R, X = lab.run_slot(s)
    busy = np.sum(X - lab.SIG.m1.values[rr])
    print(f"{s:4s} signals {len(rows_all):5d} | taken {len(rr):4d} | arrived while busy {len(rows_all)-len(rr):5d} | slot in a trade {busy/tot_min*100:4.1f}% of trading minutes"
          f" | signals per week {len(rows_all)/82:.1f}")
