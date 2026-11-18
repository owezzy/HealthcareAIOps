# 0011: Bounded contexts with hexagonal layering; shared contracts package

- **Status:** Accepted
- **Date:** 2026-11-17

## Context
Several processes (API, agent, executor, sim, evals) must agree on the same vocabulary and scenario ground truth, and use cases must be testable without infrastructure.

## Decision
- `packages/contracts` (`aiops_contracts`) holds every cross-process schema and enum. It depends on nothing else in the repo.
- Each service is organised by bounded context, then by layer (`domain`, `ports`, `use_cases`, `http`, `adapters`), with dependencies pointing inward and wiring only in `app.py`.
- Ports exist only where a real adapter and an in-memory fake both exist.

## Consequences
- Use-case tests run without a database.
- A contract change is visible in one package and caught by every consumer's tests.
