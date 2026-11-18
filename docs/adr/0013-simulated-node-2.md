# 0013: Simulate node-2 as a K3s node in a Docker container

- **Status:** Accepted (files and scripts ready; not yet applied to the server)
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

## Risk assessment (2026-11-18)
Evidence: read-only checks on `owezzy-db`, K3s documentation, k3d's cgroup v2 entrypoint and K3s issues #13072 and #6054.

| Risk | Finding | Remediation in `deploy/node2/` |
|---|---|---|
| cgroup v2 nesting stops the kubelet (`EBUSY` enabling controllers) | Host is cgroup v2 with all controllers delegated; Docker 29 uses a private cgroup namespace. Whether `rancher/k3s` prepares cgroups itself is undocumented | `entrypoint.sh` moves processes into a child cgroup and delegates controllers, the Docker-in-Docker technique k3d also uses |
| Recreated container cannot rejoin ("Node password rejected") | K3s keeps a node password in `/etc/rancher/node`; losing it, or a leftover secret, blocks the name | Volume for `/etc/rancher/node`; `rollback.sh` deletes the `node-2.node-password.k3s` secret |
| Pods on node-2 get unusable DNS | A custom Docker network gives the container `127.0.0.11`, which K3s rejects as loopback | Kubelet uses `resolv.conf` with public resolvers; cluster DNS still goes through CoreDNS |
| Node advertises the host's full 8 GiB, so the scheduler overcommits it | The kubelet reads host memory, not the container cap | Container capped (512 MiB, 1 CPU, 2,048 PIDs); the estate namespace gets a ResourceQuota (week 2 manifests) |
| A broken node affects production | Host evicts production pods below 500 MiB free; no DaemonSets exist, so nothing auto-lands on a new node | Joins with a canary `NoExecute` taint; `verify.sh` must pass before `--promote`; `preflight.sh` refuses below 1,100 MiB free |
| Networking between host and container | Modules `overlay`, `br_netfilter`, `vxlan` loaded; forwarding on; flannel VXLAN; the API certificate covers `161.97.181.164` | Two ufw rules scoped to `172.31.250.0/24`; `verify.sh` proves cross-node DNS through VXLAN |

Residual risk: the agent-beside-native-server combination is not documented by K3s or k3d, so it is proven only by `verify.sh` on the real host. The canary flow makes a failed attempt cost nothing but a rollback.

## Consequences
- S5 is a real node failure, not a cordon-and-drain imitation, at no extra cost.
- Memory: up to 512 MiB more on a host that reserves 3 GiB for the system and evicts below 500 MiB free. Keep the estate small.
- Running K3s in Docker next to a host K3s is the least-proven part of the setup (cgroup v2 nesting, VXLAN through the bridge). The how-to has verification and a clean rollback. If it proves unreliable, the fallback is S5 limited to cordon-and-evict, recorded in a new ADR.
- The node shares the host, so it is a failure-domain simulation only. It says nothing about real hardware redundancy.
