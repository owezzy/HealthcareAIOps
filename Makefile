# Healthcare AIOps: common commands. `make help` lists them.
# `make dev` runs api + agent + runtime + web together; Ctrl-C stops all four.
# Postgres first: `make db` (Docker) or point AIOPS_DATABASE_URL at your own, then `make migrate`.

.DEFAULT_GOAL := help
.PHONY: scenario scenario-reset scenario-status manifests help install install-py install-runtime install-web install-hooks db migrate dev agent runtime web api test lint format build check

AGENT_PORT ?= 8123
API_PORT   ?= 8000

# Local development defaults only; real deployments inject these as secrets.
export AIOPS_DATABASE_URL   ?= postgresql+psycopg://aiops:aiops@localhost:5432/aiops
export AIOPS_INTERNAL_TOKEN ?= dev-internal-token
export AIOPS_API_URL        ?= http://localhost:$(API_PORT)
# Free local NVIDIA model via Ollama (`ollama pull nemotron-3-nano:4b`). Use fake:echo with no Ollama.
export AIOPS_LLM_MODEL      ?= ollama:nemotron-3-nano:4b

help: ## List available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: install-py install-runtime install-web install-hooks ## Install all dependencies

install-py: ## Install the Python workspace (uv)
	uv sync

install-runtime: ## Install the Copilot runtime (npm)
	cd services/copilot-runtime && npm ci

install-web: ## Install the Angular app (npm)
	cd apps/web && npm ci

install-hooks: ## Install repository Git hooks and lint tooling (npm)
	npm ci

db: ## Start local Postgres in Docker (compose.yaml)
	docker compose up -d --wait postgres

migrate: ## Apply database migrations (Alembic)
	cd services/api && uv run alembic upgrade head

dev: ## Run api, agent, runtime and web together (http://localhost:5173)
	$(MAKE) -j4 api agent runtime web

agent: ## Run the LangGraph agent (AG-UI on :8123/agent)
	uv run uvicorn aiops_agent.app:create_app --factory --port $(AGENT_PORT) --reload

runtime: ## Run the CopilotKit runtime (:4000/api/copilotkit)
	cd services/copilot-runtime && npm run dev

web: ## Run the Angular dev server (:5173, proxies /api/copilotkit and /api)
	cd apps/web && npm start

api: ## Run the domain API (:8000; needs Postgres and `make migrate`)
	uv run uvicorn aiops_api.app:create_app --factory --port $(API_PORT) --reload

test: ## Run Python tests (API adapter tests start a throwaway local Postgres)
	uv run pytest

lint: ## Lint Python, Angular, and runtime code; type-check the runtime
	uv run ruff check packages services
	npm run lint
	cd services/copilot-runtime && npm run typecheck

format: ## Format Python and frontend/backend JavaScript and TypeScript
	uv run ruff check packages services --fix
	uv run ruff format packages services
	npm run format

scenario: ## Inject a scenario's fault into the live estate, e.g. make scenario S=S2 (run on owezzy-db)
	uv run python -m aiops_sim.injector apply $(S)

scenario-reset: ## Undo the active scenario
	uv run python -m aiops_sim.injector reset

scenario-status: ## Show the active scenario, if any
	uv run python -m aiops_sim.injector status

manifests: ## Regenerate deploy/estate/estate.yaml from sim/services.yaml
	uv run python -m aiops_sim.manifests > deploy/estate/estate.yaml

build: ## Production build of the Angular app
	cd apps/web && npm run build

check: lint test build ## Everything CI should run
