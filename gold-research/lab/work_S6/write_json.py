import json
fm=json.load(open("work_S6/final_metrics.json"))
J={"slot":"S6","baseline":fm["base"],"recommended":fm["rec"],
"recommended_spec":{
 "exit":{"rule":"causal shadow-book selector, refit monthly, train = S6+S3 signals whose outcome is known before the month; score = mean(min(R,3)); pick best of 19 candidates",
   "candidates":"baseline (k70/none/slot/none/h4q50) + {k70,k90} x tp{2R,3R,none} x part{none,half@f30,slot}, all with be1, trail h4q80, rat none, ts none",
   "what_it_picks":{"k70/3R/none/be1/h4q80/none/none (idx 2280)":15,"k90/3R/none/be1/h4q80 (idx 3480)":4},
   "equivalent_fixed_policy":{"kind":"trend","sq":"k70","tp":"3R","part":"none","be":"be1","trail":"h4q80","rat":"none","ts":"none"},
   "note":"trail is irrelevant with 3R+be1 (h4q80/h4q50/none give identical results)"},
 "entry_filter":"none - no causal take/skip filter improved sumR robustly; ML filters raise PF (2.8->3.2-3.8) but cost 1-30R",
 "inputs_needed_live":["k70/k90 MAE-quantile stop multiplier (already in Assay)","slot ATR","shadow-book simulation of 19 candidate exits on past S3+S6 signals (monthly refit)"]},
"in_sample_best":fm["IS"],
"key_findings":[
 "S6 is a strict subset of S3: 100% of S6 signal bars are S3 signals; RSI<5 adds no edge (mean R per signal under k70/3R/be1: S6 0.37-0.40 vs S3-only RSI5-10 0.40). Weekly R correlation S6 vs S3 baselines = 0.88, monthly 0.9 under the new exit.",
 "Baseline is lumpy: +41.0R but top-5 days = 80% of profit and Jan-2026 alone = 15.5R; 2026Q2-Q3 = -0.6R.",
 "Replacing the f20 partial + H4 runner with a hard 3R target + breakeven(+0.05R after 1R) doubles R and spreads it: causal 85.3R (PF 2.78, 16/19 months, top5days 18%, eq_R2 0.973) vs 41.0R; every quarter except 2026Q3 is >= +10.8R.",
 "Component effects (greedy, 2025+): Assay's own f20 partial ('slot') costs ~40R vs no partial (k70/3R/be1: 46.8R vs 90.2R); be1 cuts maxDD 8.4->5.1R and lifts months 14->16; ts_half hurts (90->71R); atr2 trail is destructive (-1.5R); k50 stops are clearly worse than k70/k90.",
 "Unconstrained shadow book over all 3600 policies also learns '3R target' causally (83.3R) but with mean-R scoring it chases rare runners (no target: 59R, top5days 116%, 10/19 months) - scoring must cap R (clip at 3R) or use Sharpe.",
 "No causal entry filter beats 'take all'. Univariate effects with 6/6 quarter consistency (h4_slope50, h4_rng20_atr, h4_ret24: extended H4 trend -> worse) did not survive as online rules; LightGBM online IC 0.07-0.16 lifts PF but reduces sumR."],
"robustness_notes":[
 "Neighbourhood of the recommended exit is broad: k70/k90 x 2R/3R x part none/half@f30 with be1 all give 51-90R, 14-17/19 months, top5days 17-27%, maxDD 3.4-6.2R.",
 "Candidate grid was informed by the full-period ranking; the fully honest version (all 3600 or all 1800 be1 policies, causal) gives 83.3R / 88.2R, still >2x baseline.",
 "Recommended trades 144 vs 173: win rate falls 83%->67% and maxDD rises 3.3->5.1R (ulcer 0.99->1.22) - smoother month/quarter profile but a deeper worst drawdown.",
 "Weak months 2025-02, 2026-03, 2026-05, 2026-07 coincide with price close to D1 EMA200 (d1_dist200 7.2 vs 3.5 ATR) and adverse DXY trend; a causal d1_dist200 quintile skip gives 92.3R / maxDD 3.0 but it was found post-hoc - monitor, do not adopt yet.",
 "Portfolio: if S3 adopts the same exit, running S6 as well roughly doubles risk on the same setup; treat S3+S6 as one strategy (merge or halve S6 risk)."],
"verdict":"improves"}
json.dump(J,open("reports/S6.json","w"),indent=1); print("ok")
