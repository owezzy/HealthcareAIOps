# Scenario file format

Files: `sim/scenarios/S<n>-<slug>.yaml`. Schema: `aiops_contracts.scenarios.Scenario` (Pydantic, unknown fields rejected). Catalogue: `sim/services.yaml`, schema `aiops_contracts.catalogue.Catalogue`.

## Top level

| Field | Type | Rule |
|---|---|---|
| `id` | string | `S` followed by digits; unique |
| `title`, `summary` | string | |
| `fault` | object | See below |
| `expected_signals` | list, at least one | See below |
| `ground_truth` | object | See below |
| `response` | object | See below |
| `variants` | list | Optional |

## `fault`

| Field | Type | Rule |
|---|---|---|
| `target` | component ID | Must equal `ground_truth.root_cause.component` |
| `type` | root-cause category | Must equal `ground_truth.root_cause.category` |
| `description` | string | |
| `parameters` | map | Read by the fault injector; unknown keys are refused. See below |

### Fault parameters the injector understands

| Key | Effect |
|---|---|
| `db_pool_size_to`, `version_to` (with `_from` values) | Rollout of the target with new `DB_POOL_SIZE` and `APP_VERSION` |
| `memory_limit_mi` (with informational `working_set_mi`) | Memory request and limit lowered on the target |
| `cpu_limit_millicores` | CPU limit on the target |
| `login_rate_per_second` | Load generator rate (with `cpu_limit_millicores`) |
| `used_percent` | Admin toggle `volume_used_percent` on the one application that writes to the target volume |
| `days_to_expiry` | Admin toggle `certificate_days_left` on the target |
| target is `node-2` (with informational `not_ready_after_seconds`) | `docker pause` of the node container |

## `expected_signals[]`

| Field | Values |
|---|---|
| `kind` | `metric`, `log`, `alert`, `deploy`, `k8s_event` |
| `component` | component ID |
| `description` | string |

## `ground_truth`

| Field | Type | Rule |
|---|---|---|
| `root_cause` | `{component, category}` | |
| `victims` | component IDs | Each must be downstream of the fault target (dependency or hosting) |
| `severity` | `critical`, `high`, `medium`, `low` | |
| `expected_incident_count` | integer ≥ 1 | |
| `end_state` | incident state | `resolved_with_problem` requires `response.follow_up: problem` |
| `forbidden_root_causes` | list of `{component}` | Must not include the real root cause |

## `response`

| Field | Type | Rule |
|---|---|---|
| `must_call_tools` | tool names | `get_service_health`, `get_topology`, `query_metrics`, `search_logs`, `get_recent_changes`, `get_k8s_events`, `search_runbooks`, `get_similar_incidents` |
| `acceptable_actions` | list of `{action, target, params}` | `action`: `restart_deployment`, `rollback_deployment`, `scale_deployment`. `scale_deployment` needs integer `params.replicas` inside the component's `scaling` range |
| `forbidden_actions` | same shape | No overlap with `acceptable_actions` |
| `escalation` | string or null | |
| `follow_up` | `problem`, `change` or null | With no acceptable action, `escalation` or `follow_up` is required |

## `variants[]`

| Field | Values |
|---|---|
| `id` | kebab-case, unique within the scenario |
| `kind` | `timing_noise`, `missing_data`, `conflicting_evidence`, `prompt_injection`, `poisoned_retrieval`, `permission_denied` |
| `description` | string |

## Vocabularies

| Name | Values |
|---|---|
| Root-cause category | `bad_config_change`, `resource_exhaustion`, `capacity`, `certificate`, `infrastructure_fault`, `dependency_degradation`, `unknown` |
| Incident state | `open`, `investigating`, `awaiting_approval`, `mitigating`, `mitigated`, `resolved`, `resolved_with_problem` |
| Component kind | `application`, `database`, `volume`, `node` |
| Clinical tier | `1` care affected within minutes, `2` workaround exists, `3` non-clinical |
