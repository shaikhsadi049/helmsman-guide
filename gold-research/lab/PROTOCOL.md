# LAB PROTOCOL — per-strategy deep analysis (XAUUSD robot "Assay")

You are one researcher in a team. Each researcher owns ONE strategy (slot) of the gold robot and must find, from the
market's own behaviour, how that strategy should ENTER (take/skip), STOP, TAKE PROFIT, TRAIL and BOOK PROFIT so its
equity curve rises as SMOOTHLY as possible. The owner wants a strategy that adapts to the market at every moment and
does not trade when its trades would lose.

## Hard rules (the owner's)
1. **Only 2025-01-01 .. 2026-07-30 matters.** Signals before 2025 exist only as warm-up history for causal learning.
   Never cite results from earlier years.
2. **No "select on one period, test on another".** Judge on the whole 2025+ window, quarter by quarter and month by month.
3. **Everything must be causal (adaptive).** A decision about a signal at time t may use only information known before t:
   features are already causal; outcomes of earlier signals are known only after their exit bar
   (`lab.known_bar`). Use the online learners in `lab.py` (`online_predict`, `online_best_policy`) or write your own with
   the same rule (refit monthly, train only on outcomes known before the month starts). This is exactly what the live
   EA can do, so this is the honest number.
   You MAY also report a full-period "best fixed choice" but label it IN-SAMPLE (optimistic) and always show its causal
   counterpart and its neighbourhood robustness (do nearby settings work too?).
4. Every rule/feature you recommend must be computable live in MQL5 from price/time/DXY (all lab features are).
   An exit policy chosen per signal is implementable live via a "shadow book": the EA can simulate every candidate exit
   on every signal's price path and learn which works now.
5. Be honest. If nothing beats the baseline robustly, say so. Do not over-fit: 19 months, few hundred trades per slot.
   Prefer few, strong, consistent effects (same sign in most quarters) over many weak ones.

## Data (read-only — do not modify these files or lab.py)
Directory: `/tmp/claude-0/-home-user-helmsman-guide/88707adc-3931-58c8-a73e-34371631e4fa/scratchpad/lab`
- `signals.parquet` (13,684 rows): every signal of 11 slots 2024-06..2026-07. cols: slot, kind(trend/fade), tf, m1 (1m bar index
  of the signal close; entry at the next 1m open), dir, lvl, atr (slot TF, MT5-style), atr4, mae_a/mfe_a (excursion in ATR over the
  calibration horizon; known at xend), k50..k90 (market-measured stop multiplier = quantile of recent MAE, known at signal time),
  f20..f90 (quantiles of recent favourable moves, ATR units), tw50/tw80 (H4 pullback-depth quantiles), time.
- `features.parquet` (same rows, 169 causal float features). Prefixes m5_, m15_, h1_, h4_, d1_ = timeframe; directional
  features are already SIGNED by trade direction (positive = in favour of the trade). Others: day_rng_atr, day_pos,
  day_ret_atr, prev_rng_atr, dist_prev_hi/lo, gap_atr, hour (UTC), wday, min_since_day_open, vol60_vs_day, dxy_trend/ret5/z20.
- `R.npy` [13684 x 3780] float32: net R (after $0.34/oz cost) of every signal under every exit policy; `X.npy` exit 1m bar;
  `LK.npy` first bar the stop reached breakeven (-1 never); `MF.npy` max favourable excursion in R.
- `policies.json`: list of 3780 policy dicts. Trend policies (index 0..3599): sq (stop quantile k50/k70/k90), tp (none/f50/1R/2R/3R),
  part (slot = Assay's own partial+lock, none, half@f30), be (none/be1 = stop to +0.05R after 1R), trail (h4q80 = Assay's H4
  measured trail, h4q50 tighter, atr2/atr4 = continuous chandelier 2/4 x TF-ATR, none), rat (profit ratchet: none, q90k50/q70k50 =
  after profit reaches the 90th/70th pct of recent favourable moves keep 50%, 2R_k50), ts (none / ts_half = exit at half the
  horizon if not in profit). Fade policies (3600..3779): sq, tp (f30/f50/f70 measured, 1R, mean = back to the 20-bar mean),
  be, rat, hm (horizon x0.5/1/2).
- `lab.py`: `SIG`, `load_F()`, `load_R()`, `load_X()`, `baseline_policy(slot)` (= what Assay does today), `policy_index(**kw)`,
  `run_slot(slot, policy_per_signal, take_mask)` (one position at a time per slot, 2025+), `metrics(R, times)` (smoothness
  report: eq_R2, months_pos, weeks_pos_pct, ulcer_R, maxDD_R, top5days_pct, PF, sumR ...), `online_predict`, `online_best_policy`,
  `known_bar`, `evaluate`. Import with `sys.path.insert(0, "<lab dir>"); import lab`.
- Raw prices if needed: `sys.path.insert(0, "<scratchpad>/bt"); import dyn2_run as R2` → `R2.m1` (1m OHLCV, UTC), `R2.GR[tf]`
  (bars per TF). Loading takes ~30-60 s.

## What to do for your slot
A. Baseline: `lab.evaluate(slot)`; monthly R table; where the losses/flat periods are.
B. Exits: metrics of EVERY policy of your kind on your slot (vectorised: R[rows, j] with greedy via run_slot is slow for
   3600 policies — first rank policies by simple per-signal mean/median R and quarter consistency on all 2025+ signals,
   then run_slot on the top ~50 and on neighbours). Which components matter (stop q, target, partial, trail, ratchet,
   breakeven, time stop)? Is there a regime (volatility rank, trend efficiency, ADX, H4 stack, day range, hour, momentum...)
   where a different exit is clearly better? Build a causal adaptive exit (online_best_policy with a regime feature, or
   per-policy online regressors and argmax) and compare to the best single fixed policy.
C. Entry take/skip: univariate analysis of all 169 features (quintile mean R under your chosen exit, consistency by
   quarter), strongest pairs, then causal filters: online rules (thresholds learned from past data only) and online ML
   (`online_predict`; try feature subsets, classification of "loss" vs "win", pooling with sibling slots of the same kind
   with a slot indicator to get more data). Skip a signal when the causal prediction says it will lose.
D. Diagnose the losing/flat months: what was the market doing (feature means) vs good months.
E. Combine B + C into ONE recommended causal spec for the slot; compare against baseline with `metrics`.

## Output (required)
Write `<lab dir>/reports/<SLOT>.md` (English, concise, tables) and `<lab dir>/reports/<SLOT>.json` with:
`{"slot":..., "baseline": metrics, "recommended": metrics, "recommended_spec": {"exit": policy dict or adaptive rule,
"entry_filter": description, "inputs_needed_live": [...]}, "in_sample_best": metrics, "key_findings": [...],
"robustness_notes": [...], "verdict": "improves|no robust improvement|drop slot"}`.
Put your scripts in `<lab dir>/work_<SLOT>/`. Use `num_threads=1` for LightGBM; avoid running more than one heavy process
at a time (4 CPUs shared by 10 researchers). Keep each script under ~10 minutes of runtime.
Your final message: a short summary of the verdict and the 3-6 most important findings with numbers.
