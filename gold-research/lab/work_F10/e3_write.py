import json
L="/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab/"
N=json.load(open(L+"work_F10/final_numbers.json"))
f10={"slot":"F10","baseline":N["F10"]["base"],"recommended":N["F10"]["causal_target"],
 "recommended_spec":{"exit":{"rule":"causal target selection: each month pick, among k70-stop / 1x-horizon fade exits with targets {f30,f50,f70,1R,mean}, the one with best mean R on past resolved F10 signals (lab.online_best_policy, prior 20). It selected 'mean' in every month 2025-01..2026-07, so in practice:",
   "policy":{"kind":"fade","sq":"k70","tp":"mean","be":"none","rat":"none","hm":1.0},
   "plain":"stop = k70 x ATR (min 0.3), take whole position when price returns to the 20-bar mean (M30), time exit 480 min"},
  "entry_filter":"none (no causal filter beat the no-filter result robustly)",
  "inputs_needed_live":["M30 20-bar SMA (target)","k70 MAE quantile (existing)","M30 ATR","shadow book of 5 target variants on past F10 signals to keep re-checking the choice monthly"]},
 "in_sample_best":dict(N["F10"]["insample"],policy="k70/1R/none/none/hm0.5 (IN-SAMPLE, best ret/DD; highest sumR fixed policy is k50/mean/be1/q70k50/hm2 = 18.5R but maxDD 4.5)"),
 "key_findings":[
  "Exit target is the lever: with the k70 stop, every target/horizon except f30 beats the baseline f50 target (k70 row: 1R 14.2-14.9R, mean 13.1-16.2R, vs f50/h1 10.3R).",
  "Causal online target selection (lab.online_best_policy over 5 targets at k70/h1) picks 'mean' from the first month using only warm-up outcomes and keeps it: 79 trades, PF 1.67, +16.2R, maxDD 2.7R, eq_R2 0.931, top5 days 49% (baseline PF 1.43, +10.3R, DD 3.2, R2 0.852, top5 71%). Same choice with pooled F8-F11 history: +15.6R.",
  "Stop: k70 dominates (avg over all targets/horizons: PF 1.55, DD 3.0R) vs k50 (PF 1.30, DD 5.7R) and k90 (PF 1.60 but only 6.4R). Breakeven (be1) and the q70k50 ratchet are near no-ops (identical R on most signals).",
  "Shorter horizon (hm0.5 = 240 min) with 1R target is the smoothest IN-SAMPLE choice (PF 1.99, DD 1.7R, ulcer 0.73, 15/18 months) but the causal learner does not reliably find it when horizon is a candidate dimension (k70 15-policy set: +9.7R).",
  "Entry: best features form a coherent 'already bouncing' family (signed m15_ret12/ret24, m5_rsi2, m5/m15 dist20, m5_streak; IC -0.22..-0.29, same sign in 6-7/7 quarters): fades that have already started reverting before entry do worse. Pair m5_rsi2>median & m15_ret12>median: mean R -0.36 vs +0.38, worse in 7/7 quarters (baseline exit). But max |IC| 0.29 is at the permutation-noise level and causal filters add nothing on top of the 'mean' exit (gated pair +15.9R, composite +16.6-16.8R vs +16.2R).",
  "Online ML (LightGBM, own or pooled F8-F11 with slot indicator, 4 feature subsets, reg/cls): out-of-sample IC -0.10..+0.13; best +16.4R with 60 trades, 15 of 16 configs below +16.2R. Online threshold rules: +3.2..+16.6R. No robust entry filter.",
  "Losing months (2025-04, 2025-11, 2026-01, 2026-02, 2026-04; -3.5R over 23 trades) are high-volatility expansion months (d1/h4/h1 atr_pct +1.3..+1.4 SD vs good months, lower M5/M15 range-efficiency). Volatility skip-rules cost more winners than losers (gated d1_atr_pct-high skip: +10.4R)."],
 "robustness_notes":[
  "The 'mean' target win does NOT replicate on sibling fades F8/F9 (there f50 is better at k70/h1), so it is F10-specific; it is however what the causal learner chose from F10's own warm-up history and kept every month.",
  "Neighbourhood: k70/mean at hm 0.5/1/2 = 13.1/16.2/13.8R; k70/1R at hm 0.5/1/2 = 14.7/14.2/14.9R; all above baseline 10.3R with DD <= 3.1R.",
  "Quarterly (recommended): +3.2, -1.0, +3.5, +2.1, +2.5, +1.7, +4.2R; 2025Q2 (April 2025 volatility spike) remains the only losing quarter, as in baseline.",
  "Only 111 signals 2025+ (79 taken); a 6R improvement is ~0.07R/trade. Keep the shadow book running: if f50/1R overtakes 'mean' on past resolved signals, the learner switches automatically.",
  "A filter-plus-exit combination (bounce composite skip + k70/1R/hm0.5) reached +18.4R PF 2.62 DD 1.7 in testing, but both pieces were chosen in-sample; not recommended."],
 "verdict":"improves"}
f11={"slot":"F11","baseline":N["F11"]["base"],"recommended":N["F11"]["base"],
 "recommended_spec":{"exit":{"policy":{"kind":"fade","sq":"k70","tp":"f50","be":"none","rat":"none","hm":1.0},"plain":"keep baseline: stop k70 (min 0.3), whole position at f50, time exit 720 min"},
  "entry_filter":"none adopted. Shadow-test candidate: skip when h4_er30 < past 25th percentile of F11 signals, switched on only while past resolved F11 signals in that tail have negative shrunk mean R (gate was on in all 17 months).",
  "inputs_needed_live":["H4 efficiency ratio over 30 bars (for the shadow candidate)","k70, f50 (existing)"]},
 "in_sample_best":dict(N["F11"]["insample"],policy="k70/f30/none/none/hm1.0 (IN-SAMPLE; highest sumR fixed = k50/f70/be1/hm2 18.7R but DD 5.4, R2 0.74)"),
 "candidate_h4er30_gate":{"n":60,"PF":1.73,"sumR":10.5,"maxDD_R":3.4,"months_pos":"13/17","q_pos":"5/7","eq_R2":0.935,"ulcer_R":1.39,"top5days_pct":59.0,"label":"feature chosen in-sample (2nd best of 336 gated rules); threshold and activation causal"},
 "key_findings":[
  "Baseline is weak and lumpy: PF 1.28, +5.6R, top-5 days 111% of profit, 4/7 quarters positive; 2025Q1 (-1.4R) and 2026Q3 (-2.0R) negative.",
  "Exits: f30 target is the most robust cell family (positive in all 9 stop x horizon cells, +4.5..+14.2R, PF 1.4-1.7); k70/f30/h1 IN-SAMPLE = +8.1R, PF 1.50, DD 3.0. Longer horizon (hm2 = 1440 min) helps on average (+9.2R vs +5.1R at hm1). be1/ratchet are near no-ops.",
  "But the causal learner does not find a better exit: online target selection at k70/h1 keeps f50 (104/111 signals) -> +4.7R; with regime buckets results scatter +1.5..+17.4R (median ~6-11R depending on set) - no stable regime-dependent exit.",
  "Entry: strongest univariate effects are daily-timeframe (d1_streak, d1_rsi2, d1_z20; |IC| 0.27-0.32) but inconsistent (2-4/7 quarters). Online ML: every one of 16 configs is below baseline (-0.3..+5.2R). Online threshold rules: -1.1..+8.6R.",
  "h4_er30 low (choppy H4) is bad for F11 (tercile means -0.25/+0.18/+0.34R, IC +0.31) and also for F10 and F9 in 2025+; a causally gated skip of the bottom quartile gives +10.5R PF 1.73 DD 3.4 top5 59% and is robust to the cut (q20/25/33/40: +9.6/10.5/11.7/10.1R). But it is the 2nd best of 336 equally-gated single-feature rules (median +5.6R, 95th pct +7.5R), so selection bias cannot be excluded.",
  "Losing months (2025-01/02/04, 2026-03/07; -8.2R over 22 trades) have low daily volatility rank (d1_atr_rank -1.1 SD) and low D1/H4 variance ratio - quiet, directionless markets where a false breakout has nowhere to revert to - but volatility gates did not help causally (+2.5..+6.4R)."],
 "robustness_notes":[
  "~111 signals 2025+ (70 taken): one extra 2R winner moves sumR by a third; treat all F11 differences under ~5R as noise.",
  "Multiple-testing check: gated rule scan over all 169 features x 2 tails -> sumR median 5.6, 5-95% 2.0..7.5R; only 2 rules >= 10.5R.",
  "No exit or entry change passed both the causal test and the neighbourhood/selection test, so the baseline stays."],
 "verdict":"no robust improvement"}
for d in (f10,f11): json.dump(d,open(L+f"reports/{d['slot']}.json","w"),indent=1)
print("ok")
