from common import *
import pickle, json
ms=np.load("ms.npy"); F=F7()
fi=pickle.load(open("final.pkl","rb"))
def thr(f,qq,known):
    x=F[f].values; take=np.ones(len(rows),bool)
    for a,b in zip(ms[:-1],ms[1:]):
        te=(M>=a)&(M<b); take[te]=~(x[te]>np.nanquantile(x[M<a],qq))
    return take
isb=lab.metrics(*(lambda i,R:(R,T[i]))(*run(130,thr("h1_adx",0.7,None))))
print("in-sample best", isb)
def clean(m): return {k:(float(v) if isinstance(v,(np.floating,np.integer)) else v) for k,v in m.items()}
small12=[pname(pidx(sq=s,tp="none",part=p,be="none",trail="h4q80",rat=r,ts="none")[0]) for s in ("k50","k70") for p in ("slot","none") for r in ("none","q90k50","2R_k50")]
J=dict(slot="S7", baseline=clean(fi["mb"]), recommended=clean(fi["mrec"]),
 recommended_spec=dict(
  exit=dict(rule="shadow-book adaptive exit: at the start of each month, for each of 12 candidate exits simulate the slot's own one-at-a-time trade stream on all past signals (outcomes known only after their exit bar) and pick the candidate with the highest sumR / ulcer_index of that past stream (expanding window, min 10 resolved trades)",
            candidates=[dict(P[pidx(sq=s,tp="none",part=p,be="none",trail="h4q80",rat=r,ts="none")[0]]) for s in ("k50","k70") for p in ("slot","none") for r in ("none","q90k50","2R_k50")],
            realised_choice="2025-01: k70/no-partial/h4q80 trail; 2025-02..04: k50/no-partial/h4q80; 2025-05 onward: k50/no-partial/h4q80 + ratchet q90k50 (after open profit reaches the f90 measured favourable move, keep 50% of it)",
            static_equivalent=P[82]),
  entry_filter="skip the signal when H1 ADX(14) at signal time is above the 80th percentile of H1 ADX over all earlier S7 signals (threshold recomputed monthly, past signals only). Skips ~25% of signals; neighbours q70/q90 and alternatives h4_rng20_atr/h1_ribbon/h4_di (all 'over-extended trend' measures) give the same effect.",
  inputs_needed_live=["M3/H4 ATR and measured k50/k70 MAE quantile stop (as today)","f90 quantile of recent favourable moves (ATR units, as today's f20)","H4 close trailing h4q80 (as today)","H1 ADX(14) and its running 80th percentile over past S7 signals","shadow book: per-candidate simulated outcomes of every past S7 signal (12 candidates)"]),
 in_sample_best=dict(spec="IN-SAMPLE: fixed exit k50/no TP/no partial/be1/h4q50 trail/ratchet q90k50 + skip h1_adx>past q70", metrics=clean(isb)),
 key_findings=[
  "Assay's own partial+lock (+0.1R at TP1=f20) is what kills S7: removing it (part=none) roughly doubles the median result over all 1200 matching policy pairs (median sumR 43.5 vs 21.2) and was already visible in the 2024 warm-up, so every causal selector chose part=none from Jan-2025.",
  "With no partial, a profit ratchet (q90k50 or 2R_k50) is the main smoother: top-5-days share drops from 112-160% to 50-70% and maxDD from 15-17R to 6-10R at similar sumR. Trail type (h4q80/h4q50/none) barely matters; atr2 chandelier destroys the edge; fixed TPs (1R/2R/3R/f50) are worse than no TP.",
  "Ratchet was NOT supported by the 2024 warm-up (flat there), so the causal shadow-book only adopts it from 2025-05; the honest adaptive result is +80.2R/DD 6.2 vs in-sample fixed best +95.5R/DD 5.3.",
  "Entry: the losing S7 signals are breakouts into an already over-extended trend: h1_adx Spearman -0.21 vs clipped R, Q5-Q1 sign same in 7/7 quarters, and same sign in the 2024 warm-up (-0.17). Skipping H1 ADX > causal q80 adds +2..+6R and cuts maxDD 1-3R on every exit tested (incl. baseline: +24.8R->+29.9R, DD 7.5->6.1). ML filters (LightGBM online, all features / causally selected / pooled with S1-S6) were unstable across seeds and feature sets and not better than the single rule.",
  "Losing months (2025-01,05,06, 2026-02,03,07) are low-trend months: D1 efficiency ratio 0.16 vs 0.33, H4 ADX 23 vs 30, half as many signals. But gating on D1/H4 efficiency or ADX causally did not reduce drawdown (DD 7-12R), so it is not recommended.",
  "S7 remains a runner strategy: 35% win, top 5 trades = 58.7R of 80.2R; monthly correlation with the S1-S6 trend book is 0.86 and it loses in the same months the book loses (2026-03, 2026-07)."],
 robustness_notes=[
  "8 causal shadow-book variants (candidate set small12/fam24 x objective ret/maxDD or ret/ulcer x expanding/9-month window), all with the ADX filter: sumR +61.7..+89.5R, maxDD 6.2..12.6R, PF 2.09..2.71, months positive 12-13/19, top-5-days 71-94%. All beat baseline sumR (+24.8) and months_pos (9/19); only some beat baseline maxDD (7.5).",
  "Causal selection on per-signal mean R (lab.online_best_policy, all 3600 policies) gives only +48R/DD 13.2 because it ignores smoothness and picks no-ratchet / 3R targets; selection objective matters.",
  "Fixed neighbourhood (in-sample): part=none + q90k50 for sq k50/k70/k90, be none/be1, ts none/half: sumR 66-90, maxDD 6.2-10. Quarter results of recommended: +11.5, +3.1, +28.0, +13.9, +14.2, +13.6, -4.1 (2026Q3 = July only).",
  "Small sample: 96 trades, effective sample smaller (long holds, median 14h, 90th pct 111h). Results depend on ~5 big runners (2025-08, 2026-01 contribute 40R).",
  "Portfolio (monthly, S1-S6 baseline sum + S7): adding recommended S7 at full weight raises total 222->302R but monthly-equity maxDD 8.2->12.3R; at 0.5x weight 262R / 10.2R. Baseline S7 at full weight: 247R / 12.6R."],
 verdict="improves")
json.dump(J,open("../reports/S7.json","w"),indent=1)
print("ok")
