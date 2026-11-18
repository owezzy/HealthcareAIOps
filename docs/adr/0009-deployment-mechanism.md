# 0009: Deployment mechanism

- **Status:** Accepted (see ADR-0012)
- **Date:** 2026-11-18

## Context
The demo runs on `owezzy-db`, a K3s node that already deploys other apps with Flux.

## Options
1. Flux watching this repository (GitOps), as the other apps on the node already do.
2. A CI job running `kubectl apply -k` with a deploy credential.

## Decision
Option 1. Flux reconciles `deploy/overlays/demo` from release tags. CI builds and pushes images to GHCR; it never holds cluster credentials.

## Consequences
- Deploying is "cut a release": git flow `release/x.y.z` → merge to `main` → tag `vx.y.z` → bump image tags in the overlay → Flux applies.
- Cluster credentials stay on the cluster.
