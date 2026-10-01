# Standing instructions from the owner (apply to every message)

## Resource use (session-limit protection)
- Pick the model and agent that fit the task's type and difficulty. Use cheaper/faster models or agents (e.g. haiku/sonnet, Explore) for simple searches, file reads and mechanical steps. Keep the strongest model for hard analysis and final judgement.
- Don't waste tokens: no unnecessary high-end models, extra agents, repeated file dumps or long narration.
- Never save resources at the cost of the quality of the work.
- Re-check these rules before processing every new message.

## Working style for the gold research (gold-research/)
- The owner wants RESEARCH and FINDINGS, not code changes. Don't edit the owner's EA (`mql5/Assay/Assay.mq5`), build robots or compile unless explicitly asked.
- Only the 2025-01 onward market matters. Don't select on one period and test on another; everything must be causal.
- "Dynamic" means market-measured constants instead of fixed ones, the best decision at each moment, and no trading when a strategy would lose.
- Write every finding with its formula, logic, reason, evidence, reliability and action in `gold-research/FINDINGS_LIST_BN.md`.
- Reply in simple Bengali with tables.
