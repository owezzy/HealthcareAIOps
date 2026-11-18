# Inspiration: the book behind the project

This project started with a book:

> Shimonski, Robert. *AI in Healthcare: How Artificial Intelligence Is Changing IT Operations and Infrastructure Services*. Hoboken, NJ: John Wiley & Sons, 2021. ISBN 978-1-119-68001-7.

It is a book about hospital *IT operations*, not clinical AI. It deals with keeping the systems behind patient care available: event and fault management, service management, metrics and reporting, workflow automation, cloud operations, and where AI fits into all of that. That framing is the reason this project monitors an EHR and a lab system rather than diagnosing anyone.

## What I took from it

| Theme in the book | Where it shows up here |
|---|---|
| Event and fault management | Alert ingestion and deterministic correlation into incidents |
| Integration with service management | Incident, Problem and Change records |
| Metrics, KPIs and reporting | The evaluation report and per-scenario timelines |
| Automation, and its limits | Approval-gated actions from a small allowlist |
| Cloud operations | K3s, GitOps, scoped service accounts |
| Healthcare IT reliability | Clinical-impact tiers and the departments each service affects |

The idea I leaned on hardest is a warning: automation can bring a service back while the underlying fault is still there. A restart that clears the symptom is not a repair. Scenario S5 exists because of it. A node fails, Kubernetes reschedules the workload, the dashboards go green, and the correct end state is still *resolved with a Problem record open*, not *resolved*. An agent that closes that incident has made the hospital less safe, however tidy the graph looks.

## What the book does not do

The book supplies the operational themes and the cautions. It is not a software specification, and it was written before today's agent frameworks existed. Every technology choice here is mine and recorded in the [ADRs](../adr/README.md): LangGraph, MCP, CopilotKit, Angular, FastAPI, Postgres and K3s, along with the scenarios, data models and evaluation design. Where the project goes beyond the book, such as prompt-injection testing or the three-model comparison, that is my extension, not the author's claim.

If the project gets something about healthcare IT wrong, that is on me, not on the book.
