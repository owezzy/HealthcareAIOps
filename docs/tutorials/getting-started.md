# Getting started: run the console locally

In this tutorial you run the whole stack on your machine: the API with its database, the LangGraph agent, the CopilotKit runtime and the Angular console. At the end you will send a message through the assistant and see the LLM budget meter read live data from the API.

It takes about 15 minutes, most of it installing dependencies.

## What you need

| Tool | Version | Check with |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.12 or later | `uv --version` |
| Python | 3.14 (uv installs it if missing) | `uv python list` |
| Node.js | 24 | `node --version` |
| Postgres | 18, local install **or** Docker | `psql --version` or `docker info` |
| make | any | `make --version` |

## 1. Install the dependencies

From the repository root:

```bash
make install
```

This runs `uv sync` for the Python workspace and `npm ci` for the runtime, the web app and the repository tooling (lint and Git hooks).

## 2. Start a database

Choose **one** of these.

**With Docker:**

```bash
make db
```

This starts Postgres 18 from `compose.yaml`, with user, password and database all named `aiops`.

**With your own Postgres:** create a database and point the API at it:

```bash
export AIOPS_DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/<database>
```

## 3. Create the schema

```bash
make migrate
```

Alembic applies every migration in `services/api/migrations/versions/`. You should see `Running upgrade  -> 0001`.

## 4. Start everything

```bash
make dev
```

This starts four processes side by side. Ctrl-C stops all of them.

| Process | Port | What it is |
|---|---|---|
| API | 8000 | FastAPI domain API |
| Agent | 8123 | LangGraph agent, served over AG-UI |
| Runtime | 4000 | CopilotKit runtime, the browser-facing proxy to the agent |
| Web | 5173 | Angular console (Vite) |

`make dev` also sets development defaults for the service token and the agent's API URL. They are listed in [Configuration](../reference/configuration.md).

## 5. Look around the console

Open <http://localhost:5173>.

1. The console opens on **Incidents**. The sections are placeholders until their features land; each one says which week it arrives.
2. Look at the **LLM budget** meter in the top bar. It reads `$0.00 / $5.00`: the console asked the API, and no LLM calls have been made today.
3. Open <http://localhost:5173/dev/components>. This is the living component sheet, with every shared component rendered with sample data from incident INC-1042.
4. Use the **Role** switcher in the top bar and choose **Viewer**. On the component sheet, the **Approve & execute** button is now disabled and a note explains why.

## 6. Talk to the agent

Open <http://localhost:5173/spike/assistant> and send a message.

The reply reads `Spike OK. Agent received: <your message>`. That message went from Angular to the CopilotKit runtime, to the LangGraph agent over AG-UI, and back. No LLM is involved yet: the spike agent only echoes, so no API key is needed.

## 7. Run the checks

```bash
make check
```

This runs the linters, the Python tests and a production build of the console. The API's database tests start a throwaway Postgres cluster on their own, so they work without `make db`.

## What you have now

- A working local stack with the same wiring as production: one public origin, with `/api/copilotkit` going to the runtime and `/api` going to the API.
- A live budget path: agent → API → Postgres → console.

## Next steps

- Read [Architecture](../explanation/architecture.md) to see where each kind of change belongs.
- Try [Add a scenario](../how-to/add-a-scenario.md) to extend the simulated hospital.
