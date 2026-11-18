# 0002: The agent proposes; only the executor executes

- **Status:** Accepted
- **Date:** 2026-11-17

## Context
Earlier plans gave the agent a restricted `execute_remediation` tool. Any execution tool in the agent's hands makes prompt injection a path to infrastructure changes.

## Decision
The agent has no execution tool. `propose_action` records a pending approval. After a human approves, the API calls `services/executor`, the only component with Kubernetes write credentials (a ServiceAccount scoped to namespace `estate`). The executor re-checks the approval hash, expiry, preconditions, cooldown and allowlist at execution time.

## Consequences
- Prompt injection can at worst produce a bad *proposal*, which policy and a human must both pass.
- One more deployable, justified by credential isolation.
