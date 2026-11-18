"""Simulated healthcare estate: one demo service per catalogue component.

Faults come from real Kubernetes changes where that is safe (a rollout that
changes DB_POOL_SIZE, a memory limit below BALLAST_MI, CPU throttling under
WORK_CPU_MS) and from admin toggles where a real fault would be destructive
(disk full, certificate expiry). Scenarios: sim/scenarios/*.yaml.
"""
