# 0012: Host the demo on the existing owezzy-db K3s node

- **Status:** Accepted
- **Date:** 2026-11-18
- **Supersedes:** the "new Contabo VPS with Traefik and cert-manager" parts of plan §10

## Context
`owezzy-db` is an existing Contabo VPS that already runs portfolio apps (SchoolCRM, GG-Garage) on K3s. A read-only survey on 2026-11-18 found:

| Resource | Total | In use | Notes |
|---|---|---|---|
| CPU | 4 vCPU (AMD EPYC, KVM) | ~24% (spiky) | 92% idle in `vmstat`, no steal |
| Memory | 7.8 GiB + 2 GiB swap | 3.4 GiB used, 4.3 GiB available | Neo4j in Docker uses ~850 MiB |
| K8s memory requests | ~4.4 GiB allocatable | 42% requested | Limits overcommitted (111%) |
| Disk | 96 GB | 16 GB used | |
| Platform | K3s v1.37.2, Flux, Cloudflare Tunnel per app | | No ingress controller or cert-manager |

## Decision
1. Deploy the app tier (web, copilot-runtime, agent, API) to `owezzy-db` in namespace `aiops-app`, following the existing conventions:
   - **Flux** watches this repository and applies `deploy/overlays/demo` from release tags (git flow: `release/*` → tag on `main` → Flux). This settles ADR-0009.
   - **Cloudflare Tunnel** `healthcare-aiops` (locally managed, created with the `cloudflared` CLI; routing in the `cloudflared-config` ConfigMap) publishes `aiops.owenadirah.com`. TLS terminates at Cloudflare; no inbound ports open.
   - The web pod's nginx routes `/api/copilotkit` to the runtime and `/api` to the API, so the tunnel needs one hostname rule.
   - **Database:** the cluster's shared Postgres (`postgres` namespace, `pgvector/pgvector:0.8.1-pg18`, retained 5 GiB volume, already used by SchoolCRM and GG-Garage) with a dedicated `aiops` database and role. Alembic owns the schema.
   - **Why the tunnel and not an ingress controller:** Traefik is disabled on this node, and port 80 serves certbot's standalone renewals for `db.owenadirah.com`. An ingress controller would need 80/443 opened, cert-manager, and would conflict with those renewals. The tunnel opens no inbound ports and matches the other apps.
2. Budget for the app tier: about 0.6 GiB of memory requests, 1.2 GiB of limits (no extra Postgres).
3. ~~For week 2, add a **second small VPS as a K3s worker**~~ *Superseded by ADR-0013: node-2 runs as a K3s node in a Docker container on this host.* Original text: for week 2, add a second small VPS as a K3s worker (tainted for the simulated estate only). The S5 node-failure scenario then stops a real node without touching the other portfolio apps, and the estate has the `node-2` the scenarios describe.

## Consequences
- No new VPS at all: the app tier runs on this node, and node-2 is simulated in Docker (ADR-0013).
- The demo shares a failure domain with other portfolio apps. The README and case study must say it is a demo environment, not high availability.
- Out of scope but noted: Postgres (5432) and Neo4j (7687) on this host accept connections from any address (TLS-only by firewall comment), and SSH allows `root` login. Restricting both is recommended.
