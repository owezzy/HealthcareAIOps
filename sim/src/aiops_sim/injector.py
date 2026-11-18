"""Fault injector: applies one scenario's fault to the live estate, and resets it.

    uv run python -m aiops_sim.injector apply S2      # or: make scenario S=S2
    uv run python -m aiops_sim.injector reset         # undo the active scenario
    uv run python -m aiops_sim.injector status

Run on owezzy-db: it drives `kubectl`, and S5 freezes the node-2 container
with `docker pause` (ADR-0013). The plan comes from the scenario's `fault`
block, not from per-scenario code:

  db_pool_size_to / version_to   rollout with new env on the target (real deploy event)
  memory_limit_mi                memory limit below the working set (real OOMKill)
  cpu_limit_millicores           CPU limit on the target, plus login_rate_per_second on the
                                 load generator (real throttling)
  used_percent                   admin toggle on the app writing to the target volume
  days_to_expiry                 admin toggle on the target
  target is a node               docker pause aiops-<node> (only node-2 exists physically)

One scenario at a time: the active one is recorded as an annotation on the
estate namespace. Reset applies the exact inverse of the active plan.
"""

import shlex
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aiops_contracts.catalogue import Catalogue, load_catalogue
from aiops_contracts.scenarios import Scenario, load_scenarios
from aiops_contracts.vocabulary import ComponentKind
from aiops_sim.manifests import DEFAULT_MEMORY, MEMORY, NAMESPACE, SIMULATED_NODE, TUNING

ACTIVE_ANNOTATION = "aiops.io/active-scenario"
BASELINE_CPU_LIMIT = "250m"
BASELINE_LOAD_RATE = "2"
KUBECTL = ["kubectl", "-n", NAMESPACE]

Command = list[str]


@dataclass(frozen=True)
class Plan:
    scenario_id: str
    apply: list[Command]
    undo: list[Command]


class InjectorError(RuntimeError):
    pass


def plan_for(scenario: Scenario, catalogue: Catalogue) -> Plan:
    target = scenario.fault.target
    params = dict(scenario.fault.parameters)
    component = catalogue.get(target)
    if component is None:
        raise InjectorError(f"{scenario.id}: unknown fault target {target!r}")
    apply: list[Command] = []
    undo: list[Command] = []
    used: set[str] = set()

    def take(*keys: str) -> list:
        used.update(keys)
        return [params[k] for k in keys]

    if component.kind is ComponentKind.NODE:
        if target != SIMULATED_NODE:
            raise InjectorError(f"{scenario.id}: only {SIMULATED_NODE} is a real node")
        used.add("not_ready_after_seconds")  # informational: Kubernetes decides the timing
        apply.append(["docker", "pause", f"aiops-{target}"])
        undo.append(["docker", "unpause", f"aiops-{target}"])

    if "db_pool_size_to" in params or "version_to" in params:
        pool, version = take("db_pool_size_to", "version_to")
        take("db_pool_size_from", "version_from")
        apply.append(_set_env(target, DB_POOL_SIZE=pool, APP_VERSION=version))
        undo.append(_set_env(target, **TUNING[target]))

    if "memory_limit_mi" in params:
        (limit,) = take("memory_limit_mi")
        used.add("working_set_mi")  # informational
        request, baseline_limit = MEMORY.get(target, DEFAULT_MEMORY)
        # Kubernetes rejects a limit below the request, so lower both together.
        apply.append(_set_memory(target, request=min(request, limit), limit=limit))
        undo.append(_set_memory(target, request=request, limit=baseline_limit))

    if "cpu_limit_millicores" in params:
        (cpu,) = take("cpu_limit_millicores")
        apply.append(_set_limit(target, cpu=f"{cpu}m"))
        undo.append(_set_limit(target, cpu=BASELINE_CPU_LIMIT))
        if "login_rate_per_second" in params:
            (rate,) = take("login_rate_per_second")
            apply.append(_set_env("loadgen", RATE_PER_SECOND=rate))
            undo.append(_set_env("loadgen", RATE_PER_SECOND=BASELINE_LOAD_RATE))

    if "used_percent" in params:
        (used_percent,) = take("used_percent")
        writer = _writer_of(target, catalogue)
        apply.append(_admin(writer, "set", f"volume_used_percent={used_percent}"))
        undo.append(_admin(writer, "clear"))

    if "days_to_expiry" in params:
        (days,) = take("days_to_expiry")
        apply.append(_admin(target, "set", f"certificate_days_left={days}"))
        undo.append(_admin(target, "clear"))

    unknown = sorted(set(params) - used)
    if unknown:
        raise InjectorError(f"{scenario.id}: no injector support for parameters {unknown}")
    if not apply:
        raise InjectorError(f"{scenario.id}: nothing to inject for fault {scenario.fault.type}")
    # Undo in reverse order of application.
    return Plan(scenario.id, apply, list(reversed(undo)))


def _set_env(deployment: str, **env: object) -> Command:
    return [
        *KUBECTL,
        "set",
        "env",
        f"deployment/{deployment}",
        *(f"{k}={v}" for k, v in env.items()),
    ]


def _set_limit(deployment: str, **limits: str) -> Command:
    joined = ",".join(f"{k}={v}" for k, v in limits.items())
    return [*KUBECTL, "set", "resources", f"deployment/{deployment}", f"--limits={joined}"]


def _set_memory(deployment: str, request: int, limit: int) -> Command:
    return [
        *KUBECTL,
        "set",
        "resources",
        f"deployment/{deployment}",
        f"--requests=memory={request}Mi",
        f"--limits=memory={limit}Mi",
    ]


def _admin(deployment: str, *args: str) -> Command:
    return [
        *KUBECTL,
        "exec",
        f"deployment/{deployment}",
        "--",
        "python",
        "-m",
        "aiops_sim.admin",
        *args,
    ]


def _writer_of(volume: str, catalogue: Catalogue) -> str:
    writers = [c.id for c in catalogue.components if volume in c.depends_on]
    if len(writers) != 1:
        raise InjectorError(f"volume {volume!r} needs exactly one writer, found {writers}")
    return writers[0]


# --- running ------------------------------------------------------------------------

Runner = Callable[[Command], str]


def run_command(command: Command) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise InjectorError(f"`{shlex.join(command)}` failed: {result.stderr.strip()}")
    return result.stdout.strip()


def active_scenario(run: Runner) -> str | None:
    value = run(
        [
            *KUBECTL[:1],
            "get",
            "namespace",
            NAMESPACE,
            "-o",
            f"jsonpath={{.metadata.annotations.{ACTIVE_ANNOTATION.replace('.', r'\.')}}}",
        ]
    )
    return value or None


def _mark_active(run: Runner, scenario_id: str | None) -> None:
    value = f"{ACTIVE_ANNOTATION}={scenario_id}" if scenario_id else f"{ACTIVE_ANNOTATION}-"
    run(["kubectl", "annotate", "namespace", NAMESPACE, value, "--overwrite"])


def apply_scenario(plan: Plan, run: Runner) -> None:
    current = active_scenario(run)
    if current:
        raise InjectorError(f"{current} is active; reset it before starting {plan.scenario_id}")
    _mark_active(run, plan.scenario_id)  # first, so a partial failure can still be reset
    for command in plan.apply:
        run(command)


def reset_scenario(plans: dict[str, Plan], run: Runner) -> str | None:
    current = active_scenario(run)
    if current is None:
        return None
    for command in plans[current].undo:
        try:
            run(command)
        except InjectorError:
            if command[:2] != ["docker", "unpause"]:  # unpausing a running node is fine
                raise
    _mark_active(run, None)
    return current


def load_plans(sim_dir: Path = Path("sim")) -> dict[str, Plan]:
    catalogue = load_catalogue(sim_dir / "services.yaml")
    return {s.id: plan_for(s, catalogue) for s in load_scenarios(sim_dir / "scenarios")}


def main(argv: list[str], run: Runner = run_command) -> int:
    plans = load_plans()
    try:
        match argv:
            case ["apply", scenario_id] if scenario_id in plans:
                apply_scenario(plans[scenario_id], run)
                print(f"{scenario_id} applied. Reset with: python -m aiops_sim.injector reset")
            case ["reset"]:
                reset = reset_scenario(plans, run)
                print(f"{reset} reset." if reset else "No scenario is active.")
            case ["status"]:
                print(active_scenario(run) or "No scenario is active.")
            case ["plan", scenario_id] if scenario_id in plans:
                for command in plans[scenario_id].apply:
                    print("apply:", shlex.join(command))
                for command in plans[scenario_id].undo:
                    print("undo: ", shlex.join(command))
            case _:
                print(f"usage: apply|plan <{'|'.join(plans)}> | reset | status", file=sys.stderr)
                return 2
    except InjectorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
