# Auto-Research Landscape Notes

Updated: 2026-06-01

## Sources Reviewed

- Karpathy `autoresearch`: small editable surface, fixed experiment budget, one primary metric, git-backed ratchet, and durable experiment logs.
  - https://github.com/karpathy/autoresearch
- RoBrain: structured memory for decisions, rationale, rejected alternatives, contradiction review, and queryable superseded decisions.
  - https://robrain.dev/
- Open-Sable: continuous local agent with multi-tier memory, self-benchmarking, regression detection, trend tracking, and JSONL audit trail.
  - https://github.com/IdeoaLabs/Open-Sable
- Hermes Agent Self-Evolution: prompt/skill evolution with explicit evals, test-suite guardrails, size limits, semantic-preservation checks, and human review.
  - https://github.com/NousResearch/hermes-agent-self-evolution
- brainctl: local-first SQLite memory, orient/work/persist lifecycle, handoff packets, and cross-agent surfaces.
  - https://www.brainctl.org/
- MARS: budget-aware planning, modular construction, and comparative reflective memory for credit assignment.
  - https://arxiv.org/abs/2602.02660

## Design Lessons Adopted

- Keep a narrow measurable loop: compare the same validation commands before and after a change.
- Persist comparison results as a ledger instead of treating terminal output as disposable.
- Treat regressions as first-class signals that should steer the next plan.
- Keep human review available for high-cost, irreversible, or ambiguous changes.
- Preserve local-first operation and avoid requiring embeddings or external model APIs.

## Implemented Follow-Up

- `auto-research compare` compares baseline and current validation commands through temporary git worktrees.
- `--ledger <path>` appends comparison outcomes to JSONL for later trend analysis and memory consolidation.
- `improve` briefs and the global skill now tell agents to compare against a prior version before deciding whether to keep tuning.

## Next Candidates

- Add a `compare history` command that summarizes the ledger trend.
- Promote repeated regression causes from the comparison ledger into reflective memory.
- Add decision records with rejected alternatives and contradiction checks.
