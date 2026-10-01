from h import *
import time
Fall = lab.load_F(); F = Fall.iloc[rows].reset_index(drop=True)
R_ = lab.load_R()
def show(tag, EX, take):
    m = met(EX, take); print(f"{tag:45s}", {k:m[k] for k in ("n","PF","sumR","maxDD_R","ret_dd","months_pos","weeks_pos_pct","eq_R2","top5days_pct")}, "skipped", int((~take[in25]).sum()), flush=True)
res = {}
for EX in (1248, 1200, 1320):
    print("==== exit", EX); show("no filter", EX, np.ones(len(rows),bool))
    y = R1[:, EX]; kn = lab.known_bar(rows, [EX])
    # (a) S1-only LGBM
    for nm, cols in [("all169", list(F.columns)), ("d1h4h1", [c for c in F.columns if c[:3] in ("d1_","h4_","h1_")]+["dist_prev_hi","dist_prev_lo","gap_atr","day_ret_atr","day_pos"])]:
        pr = lab.online_predict(rows, y, F[cols], kn, min_train=80)
        v = in25 & ~np.isnan(pr); ic = np.corrcoef(pr[v], y[v])[0,1]
        for th in (0.0, 0.1):
            show(f"S1 LGBM {nm} skip pred<{th} IC={ic:.2f}", EX, ~(pr < th))
    # (b) pooled trend slots
    pr_rows = np.where(lab.SIG.kind.values=="trend")[0]
    sl = pd.get_dummies(lab.SIG.slot.values[pr_rows]).astype(float).values
    Xp = np.hstack([Fall.values[pr_rows], sl]); yp = np.clip(np.asarray(R_[pr_rows, EX]), -1.5, 5)
    knp = np.asarray(lab.load_X()[pr_rows, EX])
    t0=time.time(); prp = lab.online_predict(pr_rows, yp, Xp, knp, min_train=300)
    pos = np.searchsorted(pr_rows, rows); pr1 = prp[pos]
    v = in25 & ~np.isnan(pr1); ic = np.corrcoef(pr1[v], y[v])[0,1]
    for th in (0.0, 0.05, 0.1):
        show(f"pooled LGBM skip pred<{th} IC={ic:.2f} {time.time()-t0:.0f}s", EX, ~(pr1 < th))
    res[EX] = dict(pooled=pr1)
    np.save(f"pred_pooled_{EX}.npy", pr1)
