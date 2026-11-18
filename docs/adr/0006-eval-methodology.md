# 0006: Eval methodology

- **Status:** Accepted
- **Date:** 2026-11-17

## Context
The portfolio's main gap is published evaluation results. Live-cluster evals are slow, costly and not reproducible.

## Decision
- Ground truth comes from `sim/scenarios/*.yaml` (validated by `aiops_contracts`).
- Cases are replayed from recorded telemetry snapshots, not the live cluster.
- Score deterministically wherever possible (root cause component and category, tools called, actions proposed, evidence IDs valid, end state). Use an LLM judge only for "does the evidence support the claim", spot-checked by hand.
- Compare against a rule-based baseline and across three models (ADR-0008).
- CI runs structural safety tests on every PR, a 10-case smoke eval on agent changes, and the full suite manually or nightly with a spend cap.

## Consequences
Results are reproducible and cheap enough to rerun after every prompt change.
