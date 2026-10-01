"""LAB helpers shared by every analysis. Judgement window: 2025-01-01 .. 2026-07 (all signals before are warm-up only)."""
import json, numpy as np, pandas as pd
D0 = pd.Timestamp("2025-01-01", tz="UTC")
SIG = pd.read_parquet("/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/signals.parquet")
_L = "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/"
def load_F(): return pd.read_parquet(_L + "features.parquet")
def load_R(): return np.load(_L + "R.npy", mmap_mode="r")
def load_X(): return np.load(_L + "X.npy", mmap_mode="r")
def load_LK(): return np.load(_L + "LK.npy", mmap_mode="r")
def load_MF(): return np.load(_L + "MF.npy", mmap_mode="r")
P = json.load(open(_L + "policies.json"))
SLOT_BASE = {"S1": ("k70", "h4q80"), "S2": ("k50", "h4q80"), "S3": ("k70", "h4q50"), "S4": ("k70", "h4q80"), "S5": ("k50", "h4q50"),
             "S6": ("k70", "h4q50"), "S7": ("k70", "h4q80")}
def policy_index(**kw):
    out = [j for j, p in enumerate(P) if all(p.get(a) == b for a, b in kw.items())]
    return out
def baseline_policy(slot):
    """the exit Assay uses today for this slot"""
    if slot.startswith("F"): return policy_index(kind="fade", sq="k70", tp="f50", be="none", rat="none", hm=1.0)[0]
    sq, tr = SLOT_BASE[slot]
    return policy_index(kind="trend", sq=sq, tp="none", part="slot", be="none", trail=tr, rat="none", ts="none")[0]
TIME = pd.DatetimeIndex(SIG.time)
def greedy(rows, exit_bar):
    """one position at a time per slot: rows sorted by time; a signal is taken only if the previous taken trade has exited"""
    take = np.zeros(len(rows), bool); free = {}
    sl = SIG.slot.values[rows]; mm = SIG.m1.values[rows]
    for k in range(len(rows)):
        if free.get(sl[k], -1) < mm[k]: take[k] = True; free[sl[k]] = exit_bar[k]
    return take
def metrics(R, t):
    """R: per-trade results (1R risk each), t: entry times. Smoothness-oriented report."""
    R = np.asarray(R, float); t = pd.DatetimeIndex(t)
    if len(R) == 0: return dict(n=0)
    o = np.argsort(t.values); R = R[o]; t = t[o]
    w = R > 0; eq = np.cumsum(R); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    day = pd.Series(R, index=t.tz_localize(None).floor("D")).groupby(level=0).sum()
    mon = pd.Series(R, index=t.tz_localize(None).to_period("M")).groupby(level=0).sum()
    qtr = pd.Series(R, index=t.tz_localize(None).to_period("Q")).groupby(level=0).sum()
    wk = pd.Series(R, index=t.tz_localize(None).to_period("W")).groupby(level=0).sum()
    tot = R.sum()
    x = np.arange(len(eq)); r2 = np.corrcoef(x, eq)[0, 1] ** 2 if len(eq) > 2 and eq.std() > 0 else 0
    ulcer = np.sqrt(np.mean((np.maximum.accumulate(np.r_[0, eq])[1:] - eq) ** 2))
    return dict(n=len(R), win=round(w.mean() * 100, 1), PF=round(R[w].sum() / max(1e-9, -R[~w].sum()), 2), sumR=round(tot, 1),
                avgR=round(R.mean(), 3), maxDD_R=round(dd, 1), ret_dd=round(tot / max(dd, 1e-9), 2),
                top5days_pct=round(day.nlargest(5).sum() / tot * 100, 0) if tot > 0 else None,
                months_pos=f"{(mon > 0).sum()}/{len(mon)}", q_pos=f"{(qtr > 0).sum()}/{len(qtr)}",
                weeks_pos_pct=round((wk > 0).mean() * 100, 0), eq_R2=round(r2, 3), ulcer_R=round(ulcer, 2))
def run_slot(slot, policy_per_signal=None, take_mask=None, since=D0):
    """apply per-signal policy choice (array of policy idx, or one int) and a take mask to one slot's signals; greedy one-at-a-time"""
    R_ = load_R(); X_ = load_X()
    rows = np.where((SIG.slot.values == slot) & (TIME >= since))[0]
    pol = np.full(len(rows), baseline_policy(slot)) if policy_per_signal is None else (
        np.full(len(rows), policy_per_signal) if np.isscalar(policy_per_signal) else np.asarray(policy_per_signal)[rows])
    tm = np.ones(len(rows), bool) if take_mask is None else np.asarray(take_mask)[rows]
    rr = rows[tm]; pp = pol[tm]
    Rv = np.array([R_[i, j] for i, j in zip(rr, pp)]); Xv = np.array([X_[i, j] for i, j in zip(rr, pp)])
    tk = greedy(rr, Xv)
    return rr[tk], Rv[tk], Xv[tk]

# ---------------------------------------------------------------- causal (online) learners
# Every decision for a signal at time t uses ONLY signals whose outcome was already known before t
# (their exit bar < t). Models are refit at the start of every month. Nothing from the future is used.
import lightgbm as lgb
MONTHS = pd.date_range("2025-01-01", "2026-08-01", freq="MS", tz="UTC")
M1 = SIG.m1.values
def month_starts_m1():
    import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/bt")
    import dyn2_run as R2
    return np.searchsorted(R2.idx.values, MONTHS.values)
_MS = None
def _ms():
    global _MS
    if _MS is None: _MS = month_starts_m1()
    return _MS
def known_bar(rows, policies):
    """outcome of a signal is known when the LAST of the candidate policies has exited"""
    X_ = load_X(); return np.max(np.stack([np.asarray(X_[rows, j]) for j in policies]), axis=0)
def online_predict(rows, y, Xf, known, min_train=120, params=None, rounds=200, weight_recent=False):
    """rows: signal indices (time sorted, incl. warm-up); y: target per row; Xf: features per row (DataFrame/array).
    Returns prediction per row (NaN before enough history or before 2025)."""
    params = params or dict(objective="regression", learning_rate=0.03, num_leaves=8, min_data_in_leaf=25, feature_fraction=0.5,
                            bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0, verbose=-1, num_threads=1, seed=7)
    Xa = np.asarray(Xf, dtype=np.float32); y = np.asarray(y, float); pred = np.full(len(rows), np.nan)
    m = M1[rows]; ms = _ms()
    for a, b in zip(ms[:-1], ms[1:]):
        test = (m >= a) & (m < b)
        if not test.any(): continue
        tr = known < a
        if tr.sum() < min_train: continue
        w = None
        if weight_recent:
            age = (a - m[tr]).astype(float); w = np.exp(-age / age.max() * 1.5)
        ds = lgb.Dataset(Xa[tr], y[tr], weight=w)
        mdl = lgb.train(params, ds, rounds)
        pred[test] = mdl.predict(Xa[test])
    return pred
def online_best_policy(rows, cands, known, regime=None, nbins=3, prior=20):
    """per signal: the candidate exit with the best shrunk mean R among PAST resolved signals of these rows
    (optionally within the same regime bucket; bucket edges = past quantiles of the regime feature)."""
    R_ = load_R(); Rm = np.stack([np.asarray(R_[rows, j]) for j in cands], axis=1)
    m = M1[rows]; ms = _ms(); choice = np.full(len(rows), cands[0])
    for a, b in zip(ms[:-1], ms[1:]):
        test = (m >= a) & (m < b)
        if not test.any(): continue
        tr = known < a
        if tr.sum() < 30: continue
        mu_all = np.nanmean(Rm[tr], axis=0)
        if regime is None:
            choice[test] = cands[int(np.argmax(mu_all))]; continue
        edges = np.nanquantile(regime[tr], np.linspace(0, 1, nbins + 1)[1:-1])
        btr = np.searchsorted(edges, regime[tr]); bte = np.searchsorted(edges, regime[test])
        best = []
        for k in range(nbins):
            sel = btr == k; nk = sel.sum()
            mu = (np.nansum(Rm[tr][sel], axis=0) + prior * mu_all) / (nk + prior)
            best.append(cands[int(np.argmax(mu))])
        choice[np.where(test)[0]] = np.array(best)[bte]
    return choice
def evaluate(slot, choice_full=None, take_full=None):
    rr, R, X = run_slot(slot, choice_full, take_full); return metrics(R, TIME[rr]), rr, R
