"""LAB step 1: every signal of the 11 Assay slots (EA-style calculations), 2024-06 .. 2026-07, plus the filter funnel."""
import sys; sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import v3_parity as V, dyn2_run as R2, adv3 as D, mr as M, strat as S
idx = R2.idx
SLOTS = {  # name: (kind, spec)
 "S1": ("trend", V.SLOTS[0]), "S2": ("trend", V.SLOTS[1]), "S3": ("trend", V.SLOTS[2]), "S4": ("trend", V.SLOTS[3]),
 "S5": ("trend", V.SLOTS[4]), "S6": ("trend", V.SLOTS[5]), "S7": ("trend", V.SLOTS[6]),
 "F8": ("fade", ("15min", "rsi2", "no4h", True)), "F9": ("fade", ("1h", "z2", "no4h", False)),
 "F10": ("fade", ("30min", "z2.5", "no4h", False)), "F11": ("fade", ("1h", "fbo", "no4h", True))}
ATR = {tf: V.sma_atr(R2.GR[tf].bars) for tf in ("3min", "5min", "15min", "30min", "1h", "4h")}
class FW:
    def __init__(s, F, a): s._F = F; s.atr = a
    def __getattr__(s, k): return getattr(s._F, k)
def fade_entries(spec):
    tf = spec[0]; G = R2.GR[tf]; F0 = G.F; r0 = M.rsi2
    G.F = FW(F0, ATR[tf]); M.rsi2 = lambda c: V.mt5_rsi(c, 2)
    try: E = M.entries(*spec)
    finally: G.F = F0; M.rsi2 = r0
    E["atr4"] = ATR["4h"][R2.G4.idx[E["m1"]]]
    return E
rows = []
for name, (kind, spec) in SLOTS.items():
    E = V.entries_ea(spec[0], spec[1], spec[2], spec[3]) if kind == "trend" else fade_entries(spec)
    m = E["m1"].astype(np.int64); n = len(m)
    df = pd.DataFrame(dict(slot=name, kind=kind, tf=spec[0], m1=m, dir=E["dir"], lvl=E["lvl"], atr=E["atr"], atr4=E["atr4"],
                           mae_a=E["mae_a"], mfe_a=E["mfe_a"], xend=E["end"]))
    for q in (0.5, 0.6, 0.7, 0.8, 0.9):   # market-measured stop multipliers at several quantiles (known at signal time)
        df[f"k{int(q*100)}"] = D.rolling_quantile_known(m, E["end"], E["mae_a"], 60, q, 2.0)
    for q in (0.2, 0.3, 0.5, 0.7, 0.9):   # favourable-move quantiles (ATR units)
        df[f"f{int(q*100)}"] = D.rolling_quantile_known(m, E["end"], E["mfe_a"], 60, q, 1.0)
    for q in (0.5, 0.8):
        df[f"tw{int(q*100)}"] = R2.trail_q(m, q)                  # H4 pullback-depth quantile (ATR4h units)
    if kind == "trend":
        tf, fam, nc, sess, qsl, qtp, lock, qtr, f1 = spec
        df["qsl"], df["qtp"], df["lock"], df["qtr"], df["f1"], df["hor"] = qsl, qtp, lock, qtr, f1, 60 * 24 * 30
    else:
        df["qsl"], df["qtp"], df["lock"], df["qtr"], df["f1"] = 0.7, 0.5, 0.0, 0.0, 1.0
        df["hor"] = M.MRH[spec[0]] * int(pd.Timedelta(spec[0]).total_seconds() // 60)
    rows.append(df); print(name, n, flush=True)
SIG = pd.concat(rows, ignore_index=True)
SIG["time"] = idx[SIG.m1.values]
SIG = SIG.sort_values(["m1", "slot"]).reset_index(drop=True)
SIG.to_parquet("signals.parquet")
print(SIG.groupby("slot").size().to_dict(), "since 2025:", (SIG.time >= "2025-01-01").sum())
