"""Trade streams for the dollar simulation, on broker bid/ask ticks: per signal R, exit bar and stop distance ($) under 4 exit variants."""
src = open("broker_tick.py").read(); exec(src.split("SQ = {")[0])
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
def pol_RX_custom(rows, j, pf_override=None, be=None, ra=None):
    sel = np.zeros(len(SIG), bool); sel[rows] = True
    risk, tp, pf, pR, lockR, be0, tkind, tw, ra0, hor, tsTv = ns["arrays"](POL[j], sel)
    if pf_override is not None and pf > 0: pf = pf_override
    R, X = sim_rows(rows, risk, tp, pf, pR, lockR, be if be is not None else be0, tkind, tw, ra if ra is not None else ra0, hor, tsTv)
    return R, X, risk
OUTD = {}
for slot in ["S1", "S2", "S3", "S4", "S5", "S6", "F8", "F9", "F10", "F11"]:
    allr = np.where(SIG.slot.values == slot)[0]; rows = allr[lab.TIME[allr] >= lab.D0]; res = {"rows": rows}
    jb = lab.baseline_policy(slot)
    if slot.startswith("S"):
        # E0: what the EA does at 0.01 lot -- the TP1 slice cannot be taken, the stop is still locked at +LOCK R
        res["E0_today_minlot"] = pol_RX_custom(rows, jb, pf_override=1e-9)
        # E1: MinLotTp1Mode=1 + BE at 1R -> no TP1 lock, Assay's H4 trail, breakeven at +1R
        p = dict(POL[jb]); j1 = lab.policy_index(kind="trend", sq=p["sq"], tp="none", part="none", be="be1", trail=p["trail"], rat="none", ts="none")[0]
        res["E1_mode1_be"] = pol_RX_custom(rows, j1)
        # E2: research exit: TP 3R + BE (stop quantile per finding 47)
        s = SIG.iloc[rows]; k = np.clip(s[SQ[slot]].values, 0.5, 8.0); risk = k * s.atr.values; n = len(rows); z = np.zeros(n); hor = np.full(n, 14400)
        R, X = sim_rows(rows, risk, np.full(n, 3.0), 0.0, np.full(n, 99.0), 0.0, (1.0, 0.05), 0, z, z, hor, None); res["E2_3R_be"] = (R, X, risk)
        # E3: E2 + giveback (after +1.5R keep half of the best profit)
        R, X = sim_rows(rows, risk, np.full(n, 3.0), 0.0, np.full(n, 99.0), 0.0, (1.0, 0.05), 0, z, np.full(n, 1.5), hor, None); res["E3_3R_be_gb"] = (R, X, risk)
    else:
        res["E0_today_minlot"] = res["E1_mode1_be"] = pol_RX_custom(rows, jb)
        jr = {"F8": REC["F8"][0], "F9": REC["F9"][0], "F10": REC["F10"][0], "F11": jb}[slot]
        res["E2_3R_be"] = res["E3_3R_be_gb"] = pol_RX_custom(rows, jr)
    OUTD[slot] = res; print(slot, {k: round(float(np.nansum(v[0])), 1) for k, v in res.items() if k != "rows"}, flush=True)
    pickle.dump(OUTD, open("dollar_trades.pkl", "wb"))
