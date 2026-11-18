# Build from the repository root:  docker build -f services/api/Dockerfile .
FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Every workspace member's metadata is needed to resolve the lockfile.
COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY services/agent/pyproject.toml services/agent/pyproject.toml
COPY services/api services/api
RUN uv sync --frozen --no-dev --no-editable --package aiops-api

FROM python:3.14-slim
RUN useradd --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
# Alembic config and migrations, run by the deployment's init container.
COPY services/api/alembic.ini services/api/alembic.ini
COPY services/api/migrations services/api/migrations
# Topology for correlation (AIOPS_CATALOGUE default: sim/services.yaml).
COPY sim/services.yaml sim/services.yaml
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8000
CMD ["uvicorn", "aiops_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
