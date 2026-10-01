import sys; sys.path.insert(0, "."); import lab, numpy as np, pandas as pd, time
F = lab.load_F(); R_ = lab.load_R()
for slot in ["S3", "S2", "F8"]:
    rows = np.where(lab.SIG.slot.values == slot)[0]; b = lab.baseline_policy(slot)
    y = np.asarray(R_[rows, b]); known = lab.known_bar(rows, [b])
    t0 = time.time(); pred = lab.online_predict(rows, y, F.iloc[rows], known)
    take = np.ones(len(lab.SIG), bool); take[rows] = ~(pred < 0)
    m0, _, _ = lab.evaluate(slot); m1, _, _ = lab.evaluate(slot, None, take)
    v = ~np.isnan(pred) & (lab.TIME[rows] >= lab.D0)
    ic = np.corrcoef(pred[v], y[v])[0, 1]
    print(slot, f"{time.time()-t0:.0f}s IC={ic:.3f}", "\n  base", {k: m0[k] for k in ("n","PF","sumR","maxDD_R","months_pos","eq_R2")}, "\n  ML  ", {k: m1[k] for k in ("n","PF","sumR","maxDD_R","months_pos","eq_R2")})
