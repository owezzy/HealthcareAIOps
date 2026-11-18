# 0001: Single agent with a fixed graph

- **Status:** Accepted
- **Date:** 2026-11-17

## Context
HRAS (an earlier portfolio project) uses a LangGraph supervisor-worker multi-agent design. Incident investigation is a sequential evidence-gathering task where one shared context is an advantage, and every extra agent multiplies the surface to evaluate and govern.

## Decision
One LangGraph agent with a fixed graph (plan §6.2): load context → plan → bounded tool loop → retrieve → assess → propose → policy check → interrupt for approval → verify.

## Consequences
- Easier to evaluate, trace and reason about safety.
- Introduce specialist agents only when an eval shows a specific failure that specialisation fixes, recorded in a new ADR.
