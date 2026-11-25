# ------------- Stage 1: Install dependencies with UV ------------------

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
	UV_LINK_MODE=copy \
	UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app
#copy only the dependency files first, so this slow layer is cached
# and only re-runs when dependencies change (not on every code edit)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


# -------------- Stage 2: small runtime image --------------

FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 1000 app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
	PYTHONUNBUFFERED=1

WORKDIR /app
COPY weather_pipeline ./weather_pipeline
COPY sql ./sql
RUN chown -R app:app /app

USER app
#download duckdb's S3 extension at build time, not on every run
RUN python -c "import duckdb; duckdb.sql('INSTALL httpfs')"

ENTRYPOINT ["python", "-m", "weather_pipeline.pipeline"]
CMD ["--help"]

