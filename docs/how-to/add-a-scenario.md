# Add a scenario

A scenario is one failure in the simulated hospital, with its ground truth. The same file drives the live demo, the fault injector and the evaluation dataset, so a scenario is also a test case for the agent.

## 1. Check the components exist

Every component the scenario mentions must be in `sim/services.yaml`. If you need a new one, add it there first, with its `kind`, clinical `tier`, `depends_on` and, for applications, `departments` and `scaling`.

## 2. Create the file

Create `sim/scenarios/S<n>-<short-slug>.yaml`, for example `S7-ehr-db-replication-lag.yaml`. Copy the structure of an existing scenario. The fields are listed in [Scenario file format](../reference/scenario-format.md).

Write the ground truth first, then the expected signals:

- `ground_truth.root_cause`: the component and category the agent must find.
- `ground_truth.victims`: components that look unhealthy but are not the cause. They must be downstream of the fault.
- `response.acceptable_actions` and `response.forbidden_actions`: what the agent may and must not propose.
- `variants`: the eval families to generate (noise, missing data, conflicting evidence, prompt injection, poisoned retrieval, permission denied).

## 3. Validate

```bash
uv run pytest packages/contracts
```

The tests load every scenario and check it against the catalogue. Typical failures:

| Message | Fix |
|---|---|
| `references unknown component` | Add the component to `sim/services.yaml`, or fix the ID |
| `victim ... is not downstream of ...` | The victim does not depend on the fault target, directly or through hosting |
| `actions both acceptable and forbidden` | Remove the action from one of the two lists |
| `outside ... scaling range` | Change `replicas` to fit the component's `scaling` range |
| `requires follow_up: problem` | `end_state: resolved_with_problem` needs `follow_up: problem` |

## 4. Update the test that counts scenarios

`packages/contracts/tests/test_sim_data.py` asserts the list of scenario IDs. Add the new ID there.
