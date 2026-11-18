# Build from the repository root:  docker build -f services/agent/Dockerfile .
FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY services/api/pyproject.toml services/api/pyproject.toml
COPY services/agent services/agent
RUN uv sync --frozen --no-dev --no-editable --package aiops-agent

FROM python:3.14-slim
RUN useradd --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY config/model-prices.yaml config/model-prices.yaml
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 \
    AIOPS_MODEL_PRICES=/app/config/model-prices.yaml
USER 10001
EXPOSE 8123
CMD ["uvicorn", "aiops_agent.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8123"]
