# Run a scenario

This guide injects one scenario's fault into the live simulated estate, watches it, and resets it. Scenarios are defined in `sim/scenarios/`; the injector builds its plan from each file's `fault` block.

Run these commands on `owezzy-db` from a checkout of the repository. The injector uses `kubectl` for every scenario and `docker` for S5.

## Before you start

- The estate is running: `kubectl -n aiops-estate get pods` shows six services and `loadgen`, all `Running`.
- The `estate-admin` secret exists (S3 and S4 use the admin toggles).
- No scenario is active: `make scenario-status` prints `No scenario is active.`

## 1. Preview the plan

```bash
uv run python -m aiops_sim.injector plan S2
```

It prints every command it will run, and the exact undo. Nothing changes.

## 2. Inject the fault

```bash
make scenario S=S2
```

The injector records S2 as active on the `aiops-estate` namespace first, so even a half-applied scenario can be reset. Only one scenario can be active at a time.

| Scenario | What changes | Expect within about 5 minutes |
|---|---|---|
| S1 | `ehr-api` rolls out with `DB_POOL_SIZE=5`, `APP_VERSION=v2.3.1` | A deploy; `ehr-api` 503s and slow requests; `db_pool_in_use` at the pool size |
| S2 | `lis` memory limit lowered to 96 Mi, below its working set | `OOMKilled` restarts; `interface-engine` `queue_depth` rising; "ORU^R01 delivery to lis failed" logs |
| S3 | `pacs` admin toggle: volume 96% used | `volume_used_ratio` 0.96; `pacs` 507 "No space left on device" |
| S4 | `patient-portal` admin toggle: certificate expires in 5 days | `certificate_expiry_days` 5; no errors |
| S5 | `docker pause aiops-node-2` | node-2 `NotReady` after about 50 s; its pods rescheduled to `owezzy-db` after 30 s more |
| S6 | `sso` CPU limit 50m; load generator at 20 requests per second | `sso` CPU throttling and slow logins; `auth_upstream_errors_total` rising across its dependants |

## 3. Watch it

```bash
kubectl -n aiops-estate get pods -w                        # restarts, rescheduling
kubectl -n aiops-estate logs deploy/interface-engine -f    # S2 delivery failures
kubectl get nodes -w                                       # S5
```

## 4. Reset

```bash
make scenario-reset
```

The reset runs the plan's undo in reverse order and clears the active marker. Rollouts settle within a minute or two; S5's rescheduled pods move back to node-2 only when they are next rescheduled.

## If something fails

| Symptom | What to do |
|---|---|
| `error: S1 is active; reset it before starting S2` | `make scenario-reset` |
| An apply command failed partway | `make scenario-reset`: the scenario was marked active first, so its undo still runs |
| S3 or S4 returns `401` or `503` | The `estate-admin` secret is missing or the pods started before it existed: create it, then `kubectl -n aiops-estate rollout restart deployment` |
| S5 fails with `docker: permission denied` | Run on `owezzy-db` as a user in the `docker` group, or as root |
