import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
src = open("combo_sim.py").read().split('if __name__ == "__main__":')
exec(src[0].replace("rp = mn + (mx - mn) * xdd * tr", "rp = (mn + (mx - mn) * xdd * tr) * (MRMUL if MRk[i] else 1.0)"))
MRMUL = 0.5
exec("\n".join(l[4:] for l in src[1].split('    tr = A_[A_.kind == "trend"]')[0].split("\n")))
B = pd.read_parquet("../combo_trades_tick.parquet")
for mx in (5, 3):
    print(f"--- max {mx}")
    row("trend only", A_[A_.kind == "trend"], mx=mx)
    MRMUL = 0.5; row("trend+4 fade x0.5 (1m fades)", A_, mx=mx); row("trend+4 fade x0.5 (TICK fades)", B, mx=mx)
    MRMUL = 0.3; row("trend+4 fade x0.3 (TICK fades)", B, mx=mx)
