import numpy as np, warnings
warnings.filterwarnings("ignore")
exec(open("aggressive.py").read().split("rng = np.random")[0])
rng = np.random.default_rng(11)
print("WEAK-MARKET STRESS: every winning trade's R halved (losers unchanged), 12-month Monte Carlo, 4000 paths")
print("variant                     | PF(stressed) | risk | median   5th pct  P(loss) P(DD>30%) P(DD>50%)")
for name, f1, pyr in (("A base (half at TP1)", 0.5, 0), ("B lock-only TP1", 1e-9, 0), ("C base + pyramid<=3", 0.5, 3), ("D lock-only + pyramid<=3", 1e-9, 3)):
    R = trades(f1, pyr).R.values; R = np.where(R > 0, R * 0.5, R); w = R > 0
    head = f"{name:28s}| {R[w].sum()/-R[~w].sum():12.2f}"
    for rp in (1.0, 2.0, 3.0):
        n = int(len(R) / 19 * 12); fin = []; dds = []
        for _ in range(4000):
            e = np.cumprod(1 + np.maximum(rng.choice(R, n) * rp / 100, -0.99)); fin.append(e[-1] - 1); dds.append((1 - e / np.maximum.accumulate(e)).max())
        fin, dds = np.array(fin), np.array(dds)
        print(f"{head} | {rp:3.0f}% | {np.median(fin)*100:+6.0f}% {np.percentile(fin,5)*100:+7.0f}% {np.mean(fin<0)*100:6.1f}% {np.mean(dds>0.3)*100:7.1f}% {np.mean(dds>0.5)*100:7.1f}%")
        head = " " * len(head)
