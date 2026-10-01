"""Which exit is right in which market behaviour? Per trend slot: classify every signal by causal regime features,
evaluate all 274 exits inside each regime cell (per-signal mean R, clipped, and consistency by quarter), then a CAUSAL test:
each month, per regime cell, pick the exit with the best past (shrunk) score and apply it this month."""
import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "../lab")
import xexit as XE, lab
SIG = lab.SIG; F = lab.load_F(); MS = lab._ms(); M1 = SIG.m1.values
SQ = {"S1": "k70", "S2": "k50", "S3": "k70", "S4": "k70", "S5": "k50", "S6": "k70", "S7": "k50"}
def tercile_past(x, known_mask):
    """regime label 0/1/2 using terciles of the feature over ALL signals (labels only for description)"""
    q = np.nanquantile(x, [1/3, 2/3]); return np.searchsorted(q, x)
REG = {  # name: (feature, labels)
 "volatility (H1 ATR rank)": ("h1_atr_rank", ["calm", "normal", "volatile"]),
 "trend running vs stalled (H1 efficiency 30)": ("h1_er30", ["stalled/choppy", "mixed", "running"]),
 "trend strength (H1 ADX)": ("h1_adx", ["weak", "medium", "strong"]),
 "daily trend (D1 ribbon with trade)": ("d1_ribbon", ["against/flat", "mild", "strong with"]),
 "day already travelled (day range / ATR)": ("day_rng_atr", ["quiet day", "normal day", "big day"]),
}
rows_out = []; causal_out = []
for slot in SQ:
    rows = np.where(SIG.slot.values == slot)[0]; s = SIG.iloc[rows]; tf = s.tf.iloc[0]
    k = np.clip(s[SQ[slot]].values, 0.5, 8.0); risk = k * s.atr.values; hor = np.full(len(rows), 14400)
    menu = XE.exit_menu(tf); RR = []; XX = []
    for ex in menu:
        R, X = XE.run(s.m1.values, s.dir.values, s.lvl.values, risk, hor, tp=ex["tp"], be=ex["be"], trail=ex["trail"], stall=ex.get("stall", 0),
                      prog=ex.get("prog", (0, 0.0)), gb=ex.get("gb", (0, 0.0)), tf_flag=tf)
        RR.append(np.asarray(R)); XX.append(np.asarray(X))
    RR = np.clip(np.stack(RR), -1.5, 5.0); XX = np.stack(XX)               # clip: no single runner decides
    live = (lab.TIME[rows] >= lab.D0); q = pd.PeriodIndex(lab.TIME[rows].tz_localize(None), freq="Q").astype(str)
    for rname, (feat, labels) in REG.items():
        x = F[feat].values[rows]; lab_ = tercile_past(x, None)
        for c in range(3):
            sel = live & (lab_ == c)
            if sel.sum() < 30: continue
            mu = RR[:, sel].mean(1); j = int(np.argmax(mu))
            qs = pd.Series(RR[j, sel]).groupby(q[sel]).mean(); base = RR[0, sel].mean()
            rows_out.append(dict(slot=slot, regime=rname, cell=labels[c], n=int(sel.sum()), best_exit=XE.describe(menu[j]), best_meanR=mu[j],
                                 noexit_meanR=base, q_pos=f"{(qs>0).sum()}/{len(qs)}", median_exit_meanR=np.median(mu)))
        # causal: per month, per cell (edges from past), choose exit with best shrunk past mean
        m = M1[rows]; choice = np.zeros(len(rows), int); known = XX.max(0)
        for a, b in zip(MS[:-1], MS[1:]):
            t = (m >= a) & (m < b)
            if not t.any(): continue
            past = known < a
            if past.sum() < 60: continue
            edges = np.nanquantile(x[past], [1/3, 2/3]); cp = np.searchsorted(edges, x[past]); ct = np.searchsorted(edges, x[t])
            mu_all = RR[:, past].mean(1)
            for c in range(3):
                pc = cp == c; mu = (RR[:, past][:, pc].sum(1) + 30 * mu_all) / (pc.sum() + 30)
                choice[np.where(t)[0][ct == c]] = int(np.argmax(mu))
        Rr = np.stack([RR[choice[i], i] for i in range(len(rows))]); Xr = np.array([XX[choice[i], i] for i in range(len(rows))])
        rr = rows[live]; tk = lab.greedy(rr, Xr[live]); mc = lab.metrics(Rr[live][tk], lab.TIME[rr[tk]])
        # comparison: same causal chooser WITHOUT regime (one global choice per month)
        choice0 = np.zeros(len(rows), int)
        for a, b in zip(MS[:-1], MS[1:]):
            t = (m >= a) & (m < b); past = known < a
            if t.any() and past.sum() >= 60: choice0[t] = int(np.argmax(RR[:, past].mean(1)))
        R0 = np.stack([RR[choice0[i], i] for i in range(len(rows))]); X0 = np.array([XX[choice0[i], i] for i in range(len(rows))])
        tk0 = lab.greedy(rr, X0[live]); m0 = lab.metrics(R0[live][tk0], lab.TIME[rr[tk0]])
        causal_out.append(dict(slot=slot, regime=rname, regime_sumR=mc["sumR"], regime_DD=mc["maxDD_R"], regime_m=mc["months_pos"],
                               global_sumR=m0["sumR"], global_DD=m0["maxDD_R"], global_m=m0["months_pos"]))
    print(slot, "done", flush=True)
pd.DataFrame(rows_out).to_parquet("regime_exit_cells.parquet"); pd.DataFrame(causal_out).to_parquet("regime_exit_causal.parquet")
