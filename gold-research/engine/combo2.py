import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
src = open("combo_sim.py").read().split('if __name__ == "__main__":')
src0 = src[0].replace("rp = mn + (mx - mn) * xdd * tr", "rp = (mn + (mx - mn) * xdd * tr) * (MRMUL if MRk[i] else 1.0)")
MRMUL = 1.0
exec(src0)
body = src[1].split('    tr = A_[A_.kind == "trend"]')[0]
exec("\n".join(l[4:] for l in body.split("\n")))
tr = A_[A_.kind == "trend"]
for mx in (5, 3):
    print(f"--- max {mx}")
    row("trend only", tr, mx=mx)
    for mul in (1.0, 0.5, 0.3):
        MRMUL = mul
        row(f"trend+4MR, MR risk x{mul}", A_, mx=mx)
        row(f"trend+MR1+MR2, MR risk x{mul}", A_[(A_.kind == "trend") | A_.slot.isin([10, 11])], mx=mx)
    MRMUL = 1.0
