import json
d=json.load(open("work_S2/dump.json"))
J={"slot":"S2","baseline":d["baseline"],"recommended":d["recommended"],
"recommended_spec":{
 "exit":{"type":"adaptive shadow-book, causal",
   "candidates":"all 240 trend exits with Assay's own stop k50 and trail h4q80 (sq=k50; tp in none/f50/1R/2R/3R; part in slot/none/half@f30; be in none/be1; rat in none/q90k50/q70k50/2R_k50; ts in none/ts_half)",
   "rule":"At the first bar of each month: for every candidate, simulate the one-position-at-a-time S2 book on all past S2 signals whose exit under that candidate is already known (expanding window from 2024-06), score = sumR / max(maxDD,1R). Take the top 8 singles, also score every half/half blend of two of them (0.5 lot on each exit, slot busy until both legs closed). Trade the month with the best-scoring single or blend.",
   "what_it_chose":"Jan-Mar 2025 and May 2025: k50/no partial/no TP/ts_half (pol 81); from Jun 2025 always a blend whose leg A = k50, no partial, 3R TP, BE(+0.05R after 1R), q90k50 ratchet, ts_half (pol 1083) and leg B = 1084/1085 (same with q70k50 ratchet) or 125 (no TP, BE, q70k50 ratchet, ts_half).",
   "static_equivalent_if_learner_not_wanted":{"legA":d["pols"]["1083"],"legB":d["pols"]["1085"]}},
 "entry_filter":"none (take every S2 signal when the slot is free). Every causal take/skip filter tested (online thresholds, online LightGBM S2-only and pooled with S1/S3-S7, side rule) reduced sumR on top of the recommended exit.",
 "inputs_needed_live":["k50 (recent-MAE stop quantile)","f70/f90 (recent favourable-move quantiles for the ratchet)","S2 TF ATR","calibration horizon (for ts_half)","shadow book: per-signal simulated outcome of each candidate exit on the 1m price path","monthly re-scoring of candidates"]},
"in_sample_best":d["is_blend"],
"in_sample_best_spec":"fixed half/half blend: leg A pol 132 (k50, no TP, no partial, BE1, ratchet q70k50, h4q50 trail) + leg B pol 1041 (k50, 3R TP, no partial, ts_half). Singles: pol 132 71.9R DD3.1 15/19; pol 1041 80.2R DD7.5 15/19.",
"key_findings":[
 "Assay's part=slot (partial/lock at +0.1R after f20) is the main drag: it turns 82.6% of trades into ~+0.15R scratches and leaves 86% of profit in the top 5 days (eq_R2 0.882). Removing it and capping the runner (3R TP or BE+q70k50 ratchet) lifts S2 to 65-80R in-sample with top5 days 30-57%.",
 "Stop k50 is clearly right: with any other component fixed, k70/k90 cut greedy sumR by 40-60% (busy slot: tighter stop = shorter trades = more signals taken). The H4 trail is irrelevant for S2 (h4q80 = h4q50 = none within 1-2R).",
 "Causal recommended spec (shadow-book blend learner): 118 trades, PF 2.56, +67.9R, maxDD 3.6R, 14/19 months, 6/7 quarters, eq_R2 0.977, ulcer 1.29, top5 days 41% vs baseline 44.6R / DD3.7 / 13/19 / 0.882 / 1.54 / 86%.",
 "Overextension at entry predicts per-signal loss consistently (h1_adx, h1_slope50, h4_rng20_atr, d1_ret3: Spearman IC -0.15..-0.21, same sign in 5-6/6 quarters) but skipping those signals does not help the book: the slot is freed and the next signal of the same impulse is taken instead. No causal entry filter beat 'take all'.",
 "Losing months (2025-05/06, 2026-03, 2026-05, 2026-07) = weak daily trend (d1_er30 0.14 vs 0.34, d1_adx 22 vs 29) and low H4 ATR rank (0.27 vs 0.58); since 2026-03 almost all S2 signals are shorts and shorts have ~0 edge (mean R +0.04..+0.09 vs longs +0.42..+0.58 per signal). Causal filters on these did not help either (too few signals to learn before the regime is over)."],
"robustness_notes":[
 "Causal learner variants: expanding 67.9R/DD3.6; 12-month window 70.2R/DD3.6/15-19; top-4 66.0R/DD3.6; top-12 63.1R/DD4.2. Scoring by plain sumR instead of sumR/DD is worse (51-58R, DD 5.8-7.5).",
 "Single-policy causal learner over the same 240 exits: 64.7-65.3R, DD5.3 (ret/DD scoring) - the blend is what keeps the DD at baseline level.",
 "Neighbourhood of the in-sample picks (one component changed, k50 kept): 132 -> 57-72R, DD 3.1-4.2 for be/rat/trail/ts/tp=3R changes; 1041 -> 52-80R. Changing part back to 'slot' or stop to k70/k90 always loses 25-45R.",
 "Recommended beats baseline in 5/7 quarters (2025Q3 20.9 vs 22.6; 2026Q3 = July only, -3.4 vs -0.9). Win rate drops from 82.6% to 55.9% - expected and acceptable for a smoother curve, but the EA operator should know.",
 "Signals are heavily clustered (1019 signals 2025+, ~115-130 trades): effective sample is small; all per-signal statistics overstate significance.",
 "Candidate set of the learner = all k50 exits (Assay's existing stop); no part of it was picked using 2025+ results. The 'top-8' and 'sumR/DD' choices are design choices, shown with neighbours above."],
"verdict":"improves"}
json.dump(J,open("reports/S2.json","w"),indent=1)
