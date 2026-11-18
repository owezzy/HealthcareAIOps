# 0003: Postgres job queue instead of RabbitMQ

- **Status:** Accepted
- **Date:** 2026-11-17

## Context
Alert volume in the demo is tens per minute. RabbitMQ adds a stateful service to run, secure and back up.

## Decision
Use a Postgres jobs table consumed with `SELECT … FOR UPDATE SKIP LOCKED`. Consumers are idempotent (keyed on alert fingerprint) with bounded retries and a dead-letter status.

## Consequences
- Transactional enqueue with the incident write; one fewer service.
- Revisit if measured throughput or fan-out needs exceed Postgres comfortably.
