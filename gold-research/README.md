# Gold (XAUUSD) strategy research — DTC family

Research log for turning the "DTC v1.36" EMA-stack indicator into a tested trading robot.

## Data
| Set | Source | Span | Use |
|---|---|---|---|
| XAUUSD 15m/1h | [ejtraderLabs/historical-data](https://github.com/ejtraderLabs/historical-data) | 2012-05 → 2022-03 | long-history robustness |
| GC futures 1m + **tick trades** (55.7M prints) | [CoderABD7000/xauusd-gc-tick-data](https://github.com/CoderABD7000/xauusd-gc-tick-data) (Databento GLBX.MDP3) | 2022-12 → 2026-07 | main research, last 2 years |

Futures rolls are Panama back-adjusted (18 rolls). Data files are not committed (≈1 GB); `engine/gcdata.py` expects them under `scratchpad/data/gc`.

## Engine
- `engine/engine.py`, `engine/gcdata.py`: TradingView-equivalent fills (signal at bar close → next open; O-H-L-C / O-L-H-C intrabar path; gap fills).
  Signals on 5m/15m/1h/4h, fills checked on every 1-minute bar.
- `engine/ticks.py`: tick-by-tick validation. 1m results match tick results within ~1% (e.g. PF 1.62 tick vs 1.63 1m).
- `engine/adv.py`: EA-style management — TP1 partial + stop lock, runner trailed on a higher timeframe, trend-break exit, profit-lock giveback.
- Costs: 0.34 USD/oz round trip (≈0.30 spread + slippage). Results in R (1R = initial risk).

## Method
Select on Y1 (2024-08 → 2025-07), judge on the **unseen** Y2 (2025-08 → 2026-07).

## Key findings (see chat log for full tables)
1. Original DTC loses on every dataset (PF 0.77–0.90).
2. Settings chosen on 2012–2022 still worked on 2024–2026 (ATR-scaled stops/trails adapt to volatility).
3. 814,320 configurations: top-50 picked on Y1 were 92–100 % profitable on Y2.
4. Runner managed by the **4H** EMA stack beats same-TF or 1H management; tight trails (1.5–2 ATR) are worst; giveback locks hurt.
5. Multi-TF high-win portfolio (S1 15m swing, S2 15m pullback+1H confluence, S3 5m pullback+15m confluence, S4 1h pullback):
   Y1 68 % win PF 2.34 +177R | Y2 68 % win PF 1.79 +134R, max DD 22.9R.
6. **Caveat:** the high win rate is made of small wins (median +0.24R); ~1 % of trades (≥10R runners) produce all net profit, concentrated in big gold trend legs.
