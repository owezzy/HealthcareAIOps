# 0005: Deterministic correlation and blast radius

- **Status:** Accepted
- **Date:** 2026-11-17

## Context
LLMs are unreliable at graph traversal and grouping, and their output varies between runs.

## Decision
Alert correlation (fingerprint, time window, topology) and blast radius (`Catalogue.dependents_of`, later a recursive SQL query) are deterministic code. The agent receives their results as evidence and explains them.

## Consequences
- S6 (alert storm → one incident) is a deterministic test, not an LLM eval.
- The agent can still disagree with the correlation, but only by citing evidence.
