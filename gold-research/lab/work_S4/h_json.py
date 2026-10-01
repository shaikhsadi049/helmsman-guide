import json
d=json.load(open("work_S4/final_metrics.json"))
out={"slot":"S4","baseline":d["baseline"],"recommended":d["k70_atr4+h4"],
"recommended_spec":{"exit":{"kind":"trend","sq":"k70","tp":"none","part":"none","be":"none","trail":"atr4","rat":"none","ts":"none","policy_index":1304,
   "note":"keep today's k70 measured stop; REMOVE the TP1 lock (+0.25R at f20/k); trail with a continuous 4 x M30-ATR chandelier instead of the H4-close h4q80 trail. be1 is a no-op here (identical results)."},
 "entry_filter":"Skip the signal when the H4 6-EMA stack is NOT aligned with the trade (h4_stack != +1), switched on causally only while past resolved h4_stack!=1 signals of S4 have mean R < 0 (min 5; it was on in all 19 months). Removes ~3% of signals. No other filter (threshold rules, online LightGBM, pooled ML, equity-curve filter) beat 'take all' causally.",
 "alternative_higher_return":{"exit":{"sq":"k50","tp":"none","part":"none","be":"be1","trail":"atr4","policy_index":144},"metrics":d["k50_atr4_be+h4"]},
 "causal_counterpart":{"rule":"monthly shadow-book: replay every one of 1757 distinct exit policies one-at-a-time on all resolved S4 signals, pick the best by sumR*eq_R2; plus h4_stack filter","metrics":d["causal_shadow+h4"],
   "converged_to":"k50/no TP/no partial/be1/h4q50 trail/ts_half"},
 "inputs_needed_live":["M30 ATR(14) (chandelier 4xATR trail)","k70 measured stop (quantile of recent MAE, as today)","H4 6-EMA stack (EMA30>35>40>45>50>60 for longs, mirror for shorts)","shadow-book R of past S4 signals with h4_stack!=1 (for the causal switch)"]},
"in_sample_best":{"by_sumR":{"policy":"k50/none/none/be1/h4q80/q90k50/ts_half","metrics":d["IS_best_sumR"]},"by_ret_dd":{"policy":"k70/1R/none/be1/atr2/q70k50","metrics":d["IS_best_retdd"]}},
"key_findings":[
 "Today's exit is close to the WORST of 3600 trend policies on S4: baseline +15.0R vs median policy +21R; 'part=slot' (TP1 lock at +0.25R) is the worst partial choice (median sumR 16.7 vs 26.2 with no partial). The lock turns 83% of trades into +0.1..+0.2R scratches and leaves the slot dependent on one runner (2026-01 = 8.7R of 15R, top-5 days 114%).",
 "Removing the lock and trailing with a 4xATR chandelier (k70 stop unchanged): +27.0R, PF 2.27, maxDD 2.1R, 15/19 months, eq_R2 0.976, top-5 days 48%; beats baseline in 5 of 6 full quarters. Neighbourhood robust: every k70/no-partial/atr4 variant (any TP, be on/off) gives 27.0-29.6R with DD 2.1-2.2R and 15/19 months; k50 gives 34-40R with DD 2.8-3.7R.",
 "Every causal (shadow-book) learner, with no in-sample knowledge, abandoned the slot lock in its first month and settled on k50/no-partial runners: +41.5R (2.8x baseline), PF 3.5, but DD 5.5R, 12/19 months, top-5 95% - i.e. causal selection maximises R, not smoothness; the smooth atr4 family is a fixed design choice (flagged in-sample).",
 "Entry: overextension features hurt per-signal R consistently (prev_rng_atr, h4_rng20_atr, h1_adx, h4_rsi14: top quintile ~0 or negative, same sign in 5-6/6 quarters) but skipping them does not improve the one-at-a-time book (next signal simply replaces the skipped one). Online LightGBM (IC 0.06-0.13, S4-only or pooled with trend siblings) and an equity-curve filter all REDUCED results.",
 "Only robust filter: H4 stack not aligned (21 of 725 signals) loses in 5/6 quarters (mean -0.20R vs +0.22R under atr4); a causal skip improves every non-runner exit (k70 atr4: 27.0R/DD2.1 -> 29.2R/DD1.1).",
 "Losing months (2025-02, 2025-05, 2026-03, 2026-07) are D1 trend breakdowns / regime flips: lower D1 distance to EMA200 (-1.0 sd), DXY trending against, high D1 ATR rank; 2026-03 is the long->short flip (all signals short since 2026-04). Shorts are weaker (mean +0.04R/signal vs +0.31R longs) but still net positive in the book (+3.4R)."],
"robustness_notes":[
 "Exit family (atr4 chandelier) was chosen with full-window information; the honest causal number is the shadow-book counterpart (+40.4R, DD 4.3R, 12/19 months with the H4 filter). Both are far above baseline; the fixed atr4 choice is smoother but not causally learned.",
 "Results are per 1R risk with one position at a time; atr4 exits hold ~10h median vs ~21h baseline, so more signals get taken (122 vs 90 trades).",
 "H4 filter rests on only 21 signals (8 book trades) - small but consistent across exits and quarters; low cost if wrong (3% of signals).",
 "2026Q3 (July only) is negative for every exit (-0.4R recommended vs -1.7R baseline).",
 "Adaptive regime-conditioned exit selection (online_best_policy with 16 regime features) gave 28-51R with DD 3-6.6R and no consistent winner - noise, not recommended."],
"verdict":"improves"}
json.dump(out,open("reports/S4.json","w"),indent=1); print("ok")
