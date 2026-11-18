# 0007: Demo authentication

- **Status:** Proposed
- **Date:** 2026-11-17

## Context
The public demo needs visitors to try different roles. A full identity provider (e.g. Keycloak) is heavy for a 16 GB single node.

## Decision (proposed)
FastAPI issues signed JWTs for seeded demo users (viewer, operator, approver, admin), with a role switcher in the UI. Production would use OIDC; the RBAC checks are written against claims, so swapping the issuer does not change authorization code.

## Consequences
Simple to run; must never be described as production authentication.
