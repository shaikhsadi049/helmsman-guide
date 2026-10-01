import sys; sys.path.insert(0, "../lab"); sys.path.insert(0, "../bt")
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from scipy.stats import spearmanr
import lab
exec(open("../lab/portfolio.py").read().split("BASE = {")[0].split("REC = {")[1].join(["REC = {", ""]) if False else "")
import importlib.util
spec = importlib.util.spec_from_file_location("P", "../lab/portfolio.py"); P = importlib.util.module_from_spec(spec)
src = open("../lab/portfolio.py").read().split('if __name__ == "__main__":')[0]
exec(compile(src, "portfolio", "exec"), P.__dict__)
OF = pd.read_parquet("of_features.parquet"); SIG = lab.SIG; R_ = lab.load_R()
rows_out = []
for slot, (legs, w) in P.REC.items():
    rows = np.where((SIG.slot.values == slot) & (lab.TIME >= lab.D0))[0]
    y = np.mean([np.asarray(R_[rows, j]) for j in legs], axis=0); y = np.clip(y, -1.5, 3)   # clip runners (robust)
    q = pd.PeriodIndex(lab.TIME[rows].tz_localize(None), freq="Q").astype(str)
    for f in OF.columns:
        x = OF[f].values[rows]; ok = np.isfinite(x)
        if ok.sum() < 60: continue
        ic = spearmanr(x[ok], y[ok]).correlation
        qs = [spearmanr(x[ok & (q == qq)], y[ok & (q == qq)]).correlation for qq in np.unique(q) if (ok & (q == qq)).sum() >= 15]
        same = np.mean(np.sign(qs) == np.sign(ic)) if qs else 0
        qt = pd.qcut(x[ok], 5, labels=False, duplicates="drop"); mq = pd.Series(y[ok]).groupby(qt).mean().values
        rows_out.append(dict(slot=slot, feat=f, IC=ic, q_same=same, n_q=len(qs), q1=mq[0], q5=mq[-1], spread=mq[-1] - mq[0]))
D = pd.DataFrame(rows_out); D.to_parquet("of_ic.parquet")
pd.set_option("display.width", 200)
strong = D[(D.IC.abs() >= 0.10) & (D.q_same >= 0.83)].sort_values(["slot", "IC"])
print("order-flow features with |IC|>=0.10 and the same sign in >=6/7 quarters:"); print(strong.round(3).to_string(index=False))
print("\nmax |IC| per slot:"); print(D.assign(a=D.IC.abs()).sort_values("a").groupby("slot").tail(1)[["slot", "feat", "IC", "q_same"]].round(3).to_string(index=False))
