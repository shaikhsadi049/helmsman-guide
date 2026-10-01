from h import *
from scipy.stats import spearmanr
F = lab.load_F().iloc[rows].reset_index(drop=True)
ms = lab._MS
cols = [c for c in F.columns if F[c].notna().mean()>0.8 and F[c].nunique()>5]
def show(tag, EX, take):
    m = met(EX, take); print(f"{tag:50s}", {k:m[k] for k in ("n","PF","sumR","maxDD_R","ret_dd","months_pos","weeks_pos_pct","eq_R2","top5days_pct")}, "skip", int((~take[in25]).sum()), flush=True); return m
def online_rule(EX, topk=1, minsp=0.15, qs=(0.6,0.7,0.8,0.9), log=False):
    y = R1[:,EX]; kn = X1[:,EX]; take = np.ones(len(rows),bool); chosen=[]
    for a,b in zip(ms[:-1],ms[1:]):
        te = (M>=a)&(M<b)
        if not te.any(): continue
        tr = kn < a
        if tr.sum()<60: continue
        X = F.loc[tr, cols]; yt = y[tr]
        sp = X.apply(lambda s: spearmanr(s, yt, nan_policy="omit")[0])
        # consistency: same sign in first and second half of the training data
        h = np.where(tr)[0]; h1, h2 = h[:len(h)//2], h[len(h)//2:]
        s1 = F.loc[h1, cols].apply(lambda s: spearmanr(s, y[h1], nan_policy="omit")[0]); s2 = F.loc[h2, cols].apply(lambda s: spearmanr(s, y[h2], nan_policy="omit")[0])
        ok = (np.sign(s1)==np.sign(s2)) & (sp.abs()>minsp)
        cand = sp[ok].abs().sort_values(ascending=False).index[:topk]
        for c in cand:
            x = F[c].values; sg = np.sign(sp[c]); best=None
            for q in qs:
                th = np.nanquantile(sg*x[tr], q)   # skip if sg*x > th ... i.e. bad side when sg<0? define skip bad side
                # bad side: low sg*x (since sg*x correlates positively with y)
                th = np.nanquantile(sg*x[tr], 1-q); bad = (sg*x[tr]) < th
                if bad.sum()<10: continue
                gain = -yt[bad].sum()
                if yt[bad].mean()<0 and (best is None or gain>best[0]): best=(gain, th)
            if best is not None:
                take[te] &= ~((sg*x[te]) < best[1]); chosen.append((str(lab.MONTHS[np.searchsorted(ms,a)].date())[:7], c, round(sp[c],2), round(best[1],2)))
    if log: print(chosen)
    return take
out={}
for EX in (1248,1200,1320):
    print("=== exit",EX); show("none",EX,np.ones(len(rows),bool))
    for topk in (1,2,3):
        for minsp in (0.15,0.2):
            t = online_rule(EX, topk, minsp, log=(topk==1 and minsp==0.15)); show(f"online rule top{topk} minsp{minsp}", EX, t)
# fixed in-sample 'stretch' composite with causal percentile ranks
S = ["d1_ret24","h4_z20","h1_adx","dist_prev_hi"]
def stretch(feats):
    sc = np.full(len(rows), np.nan)
    for i in range(len(rows)):
        past = M < M[i]   # features known at signal time (no outcome needed)
        if past.sum()<50: continue
        sc[i] = np.mean([ (F[f].values[past] < F[f].values[i]).mean() for f in feats])
    return sc
sc = stretch(S); np.save("stretch.npy", sc)
for EX in (1248,1200,1320):
    for th in (0.6,0.65,0.7,0.75,0.8,0.85,0.9):
        show(f"IN-SAMPLE stretch skip>{th}", EX, ~(sc>th))
