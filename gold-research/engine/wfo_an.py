"""Walk-forward re-optimisation: every month pick the best configs on the trailing window, trade next month."""
import numpy as np, pandas as pd
import pickle
K = pd.read_parquet("wfo_keys.parquet"); Z = np.load("wfo_monthly.npz"); R, N, W = Z["R"].astype(float), Z["N"].astype(float), Z["W"].astype(float)
ES = pickle.load(open("adv_entry_sets.pkl", "rb"))
K["tf"] = [ES[i][0] for i in K.es]
MONTHS = pd.date_range("2024-08-01", periods=24, freq="MS")

def mdd(x):
    eq = np.cumsum(x); return (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()

def wfo(sel, look=6, topn=5, minwin=0.0, mintr=15, score="rdd", start=6):
    Rs, Ns, Ws = R[sel], N[sel], W[sel]
    out_R, out_N, out_W, picks = [], [], [], []
    for m in range(start, 24):
        a = max(0, m - look)
        r = Rs[:, a:m]; n = Ns[:, a:m].sum(1); w = Ws[:, a:m].sum(1)
        tot = r.sum(1)
        eq = np.cumsum(r, 1); dd = (np.maximum.accumulate(np.concatenate([np.zeros((len(r), 1)), eq], 1), 1)[:, 1:] - eq).max(1)
        pos_m = (r > 0).mean(1)
        s = tot / np.maximum(dd, 3) if score == "rdd" else (tot if score == "tot" else tot / np.maximum(dd, 3) * pos_m)
        ok = (n >= mintr) & (w / np.maximum(n, 1) >= minwin) & (tot > 0)
        s = np.where(ok, s, -np.inf)
        if not np.isfinite(s).any():
            out_R.append(0); out_N.append(0); out_W.append(0); picks.append([]); continue
        top = np.argsort(-s)[:topn]; top = top[np.isfinite(s[top])]
        out_R.append(Rs[top, m].mean()); out_N.append(Ns[top, m].mean()); out_W.append(Ws[top, m].mean()); picks.append(top)
    x = np.array(out_R)
    return dict(R=x, tot=x.sum(), dd=mdd(x), mpos=(x > 0).mean() * 100, trades=np.sum(out_N), win=np.sum(out_W) / max(np.sum(out_N), 1) * 100, picks=picks)

if __name__ == "__main__":
    print("Out-of-sample months: 2025-02 .. 2026-07 (18 months); every month re-optimised on trailing data only\n")
    res = {}
    for tf in ["5min", "15min", "1h"]:
        sel = np.where(K.tf == tf)[0]
        for look in (6, 12):
            for topn in (1, 5, 20):
                for minwin in (0.0, 0.55, 0.65):
                    for score in ("rdd", "tot"):
                        r = wfo(sel, look, topn, minwin, score=score)
                        res[(tf, look, topn, minwin, score)] = r
        best = sorted([(k, v) for k, v in res.items() if k[0] == tf], key=lambda kv: -kv[1]["tot"])
        print(f"== {tf}: all {len([k for k in res if k[0]==tf])} WFO variants -> median total {np.median([v['tot'] for k,v in res.items() if k[0]==tf]):+.1f}R, "
              f"share profitable {np.mean([v['tot']>0 for k,v in res.items() if k[0]==tf])*100:.0f}%")
        for k, v in best[:3] + best[-2:]:
            print(f"   look={k[1]:2d} top={k[2]:2d} minwin={k[3]:.2f} score={k[4]:3s} -> tot {v['tot']:+6.1f}R  maxDD {v['dd']:5.1f}R  months+ {v['mpos']:3.0f}%  win {v['win']:3.0f}%  trades {v['trades']:.0f}")
    pickle.dump(res, open("wfo_res.pkl", "wb"))
    # multi-TF combined, using one robust a-priori variant per TF (look 12, top 5, rdd) at two win floors
    for mw in (0.0, 0.55, 0.65):
        comb = sum(res[(tf, 12, 5, mw, "rdd")]["R"] for tf in ["5min", "15min", "1h"])
        print(f"\nMULTI-TF WFO (look12, top5, minwin {mw}): tot {comb.sum():+.1f}R  maxDD {mdd(comb):.1f}R  months+ {(comb>0).mean()*100:.0f}%  monthly: " + " ".join(f"{v:+.0f}" for v in comb))
