# 0013: Simulate node-2 as a K3s node in a Docker container

- **Status:** Accepted (files ready; not yet applied to the server)
- **Date:** 2026-11-18
- **Supersedes:** point 3 of ADR-0012 (a second VPS for the estate)

## Context
Scenario S5 needs a node that really fails, and the simulated estate expects a `node-2`. A second VPS is not affordable. `owezzy-db` already runs Docker next to K3s, and the K3s API certificate includes the host's public address.

## Decision
Run `node-2` as a K3s **agent inside a Docker container** on `owezzy-db` (`deploy/node2/compose.yaml`):

- Image `rancher/k3s` at the server's exact version; privileged; capped at 512 MiB.
- Own Docker network `172.31.250.0/24`. Two firewall rules let that subnet reach the API server (6443/tcp) and flannel VXLAN (8472/udp).
- Label `aiops.io/estate=true` and taint `aiops.io/estate=only:NoSchedule`, so only the simulated estate schedules there. Estate workloads **prefer** node-2 and tolerate a not-ready node for 30 s, so S5 reschedules them onto `owezzy-db`, as the scenario expects.

How S5 fails the node (implemented with the fault injector, week 2):

1. **Preferred, in-cluster and reversible:** a privileged injector pod pinned to node-2 with `hostPID` sends `SIGSTOP` to the node's `k3s agent` process. Heartbeats stop, so the node goes `NotReady` after about 40 s. `SIGCONT` from the same pod recovers it. Containerd keeps running, so the injector survives.
2. **Fallback, manual:** `docker stop aiops-node-2` on the host, then `docker start`.

## Consequences
- S5 is a real node failure, not a cordon-and-drain imitation, at no extra cost.
- Memory: up to 512 MiB more on a host that reserves 3 GiB for the system and evicts below 500 MiB free. Keep the estate small.
- Running K3s in Docker next to a host K3s is the least-proven part of the setup (cgroup v2 nesting, VXLAN through the bridge). The how-to has verification and a clean rollback. If it proves unreliable, the fallback is S5 limited to cordon-and-evict, recorded in a new ADR.
- The node shares the host, so it is a failure-domain simulation only. It says nothing about real hardware redundancy.
