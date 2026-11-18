# Build from the repository root:  docker build -f sim/Dockerfile .
FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY services/api/pyproject.toml services/api/pyproject.toml
COPY services/agent/pyproject.toml services/agent/pyproject.toml
COPY sim/pyproject.toml sim/pyproject.toml
COPY sim/src sim/src
RUN uv sync --frozen --no-dev --no-editable --package aiops-sim

FROM python:3.14-slim
RUN useradd --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY sim/services.yaml sim/services.yaml
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8080
CMD ["uvicorn", "aiops_sim.app:create_app_from_env", "--factory", "--host", "0.0.0.0", "--port", "8080"]
