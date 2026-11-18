# Architecture decision records

Format: Status / Context / Decision / Consequences. Copy `0000-template.md` for a new one. Never rewrite an accepted ADR; supersede it with a new one.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-single-agent.md) | Single agent with a fixed graph, not multi-agent | Accepted |
| [0002](0002-agent-proposes-executor-executes.md) | The agent proposes; only the executor executes | Accepted |
| [0003](0003-postgres-queue-not-rabbitmq.md) | Postgres job queue instead of RabbitMQ | Accepted |
| [0004](0004-copilotkit-angular-integration.md) | CopilotKit integration path for Angular 22 | Accepted |
| [0005](0005-deterministic-correlation-and-blast-radius.md) | Deterministic correlation and blast radius; the LLM explains | Accepted |
| [0006](0006-eval-methodology.md) | Eval methodology | Accepted |
| [0007](0007-demo-authentication.md) | Demo authentication | Proposed |
| [0008](0008-model-selection.md) | Model comparison and default model | Proposed (versions pinned at first eval) |
| [0009](0009-deployment-mechanism.md) | Deployment mechanism: Flux GitOps from release tags | Accepted |
| [0010](0010-frontend-structure-and-signal-store.md) | Frontend feature structure and NgRx SignalStore | Accepted |
| [0011](0011-bounded-contexts-and-hexagonal-services.md) | Bounded contexts with hexagonal layering; shared contracts package | Accepted |
| [0012](0012-hosting-on-owezzy-db.md) | Host the demo on the existing owezzy-db K3s node; second worker for the estate | Accepted |
