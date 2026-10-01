import json
M=json.load(open('final_metrics.json'))
fl=lambda d:{k:(float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) else v) for k,v in d.items()}
out={"slot":"F8","baseline":fl(M['baseline']),"recommended":fl(M['recommended']),
"recommended_spec":{"exit":{"rule":"online_best_policy (lab standard, mean R, monthly refit, outcomes known before month start, all history incl. 2024-06 warm-up) choosing the STOP quantile among {k50,k70,k90}; everything else fixed",
   "candidates":[{"kind":"fade","sq":s,"tp":"f50","be":"none","rat":"none","hm":1.0} for s in ["k50","k70","k90"]],
   "fixed_parts":"target f50 (broker TP, whole position), time exit 360 min (hm=1.0), no BE, no ratchet, no trail",
   "fallback_if_no_shadow_book":{"kind":"fade","sq":"k50","tp":"f50","be":"none","rat":"none","hm":1.0}},
 "entry_filter":"none - keep today's entry (M15 RSI2<5/>95, H4 6-EMA stack not aligned, 07-20 UTC). No causal filter (14 one-feature online rules, 32 online LightGBM variants incl. pooled fades) improved the slot robustly.",
 "inputs_needed_live":["M15 RSI(2)","H4 EMA stack 30/35/40/45/50/60","M15 ATR(14)","k50/k70/k90 = rolling quantiles of recent signal MAE (ATR units)","f50 = rolling median of recent favourable moves","shadow book: R of each signal under k50/k70/k90 x f50 x 360min, monthly mean of resolved outcomes"]},
"in_sample_best":fl(M['in_sample_best']),
"in_sample_best_spec":{"kind":"fade","sq":"k50","tp":"f50","be":"none","rat":"none","hm":1.0},
"key_findings":[
 "Baseline (k70/f50/360m): 181 trades, +26.9R, PF 1.44, maxDD 7.9R, 14/18 months, 4/7 quarters; losses in 2025-01, 2025-03, 2025-10 (-4.0R) and 2026-07 (-3.1R).",
 "Only 2 of 5 exit components matter: target and time horizon. f50 target and hm=1.0 (360 min) are best or near-best in every stop row; breakeven (be1) and the q70k50 ratchet change almost nothing (identical results in most cells: fade targets are hit before they trigger); hm=0.5 is clearly worse (-35% R).",
 "Stop k50 beats k70 in all 15 tp x horizon cells (greedy sumR and ret/DD) and in per-signal mean R in all 15 cells; PF per signal is the same (~1.6-1.7 for k50/k70/k90 with f50/f70), so the gain is mostly that a tighter measured stop rarely changes the outcome but buys more R per unit risk. In-sample fixed k50/f50: +59.4R, PF 1.59, DD 7.2R, 7/7 quarters.",
 "Causal stop learner (k50/k70/k90 at f50): +45.9R, PF 1.57, DD 7.2R, ret/DD 6.4 (baseline 3.39), ulcer 2.27 (2.63), 14/18 months, 5/7 quarters. Wider causal exit menus (12-60 candidates) are unstable: +11.6R..+60.7R depending on menu/criterion, often with DD 13.2R.",
 "Costs are not the issue for this slot: median stop is ~$21 at k70 ($13 at k50), so $0.34 costs only 0.016R (0.027R). With +$0.34 and +$0.68 extra cost the recommended spec still makes +41.2R / +36.5R (PF 1.50 / 1.43). Only k50 with a 1R target is cost-fragile (+28.2R -> +14.1R).",
 "Regime skips asked about do not work at signal level: vol60_vs_day quintile means are all positive (+0.15..+0.31R base); d1 trend (d1_er10, d1_adx, d1_ret12) and vol expansion (atr_ratio on all TFs, day_rng_atr) give no negative quintile and no consistent sign; causal online versions lower sumR. Monthly diagnosis does show losing months had higher d1_adx (+1.0 sd), d1_atr_ratio (+0.7 sd), prev_rng_atr (+0.7 sd), but a causal gate on d1_adx & d1_atr_ratio removes signals that still average +0.15R and cuts sumR 45.9 -> 38.0.",
 "Online ML entry filters have no skill: Spearman(pred, realised R) = -0.09..+0.02 on 2025+ for all 16 model variants per exit; every ML skip reduced sumR (best variants only trade fewer, not better)."],
"robustness_notes":[
 "The k50-vs-k70 per-signal advantage (f50) by quarter: 2025Q1 -0.02, Q2 +0.01, Q3 +0.05, Q4 -0.08, 2026Q1 +0.01, Q2 +0.40, Q3 +0.18 R/signal: same sign in 5/7 quarters but the size is concentrated in 2026Q2-Q3 (high-volatility period). In 2025 the tighter stop is neutral, not harmful.",
 "Recommended vs baseline differ only in 7 months (same policy chosen otherwise); +16R of the +19R gain comes from 2026-05 and 2026-07. eq_R2 is slightly lower (0.751 vs 0.779).",
 "One-at-a-time greedy makes results path dependent: k70 rows look worse than both k50 and k90 in greedy runs while per-signal (ungreedy) means are monotone k50>k70>k90 in R and PF is flat; treat greedy differences <~10R as noise.",
 "k90/f50 (in-sample) has the smallest DD (2.7R, +23.7R, 7/7 quarters) - an option if the owner prefers a flatter curve at lower R, but the ungreedy per-signal ret/DD favours k50 (8.8 vs 6.3).",
 "Regime-dependent exits via online_best_policy with 14 regime features: only h4_er10 looked better (+58.7R, DD 9.3) - one of 14 tries, not credible; most regime variants were worse than the no-regime learner.",
 "Shorts made +27.6R and longs -0.7R under the baseline in a gold bull market; a causal direction rule did not help (sumR 26.9->24.8) - do not filter by direction."],
"verdict":"improves"}
json.dump(out,open('../reports/F8.json','w'),indent=1)
