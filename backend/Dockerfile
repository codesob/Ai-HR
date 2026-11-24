# syntax=docker/dockerfile:1.7
# One image recipe for every backend service:
#   docker build --build-arg SERVICE=matching-engine-svc --build-arg WITH_ML=true -t aihr/matching-engine-svc backend/
ARG PYTHON_VERSION=3.14

FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS deps
ARG WITH_ML=false
RUN python -m venv /opt/venv && mkdir -p /opt/models
ENV PATH=/opt/venv/bin:$PATH HF_HOME=/opt/models
COPY requirements.txt requirements-ml.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$WITH_ML" = "true" ]; then \
      pip install -r requirements-ml.txt --extra-index-url https://download.pytorch.org/whl/cpu && \
      python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"; \
    fi

FROM base AS runtime
ARG SERVICE
ARG APP_MODULE=app.main:app
ENV PATH=/opt/venv/bin:$PATH \
    HF_HOME=/opt/models \
    HF_HUB_OFFLINE=1 \
    APP_MODULE=${APP_MODULE} \
    WEB_CONCURRENCY=2 \
    SERVICE_NAME=${SERVICE}
RUN useradd --create-home --uid 10001 app
COPY --from=deps /opt/venv /opt/venv
COPY --from=deps /opt/models /opt/models
COPY shared ./shared
COPY alembic.ini ./
COPY migrations ./migrations
COPY ${SERVICE}/ ./
RUN mkdir -p uploads knowledge && chown -R app:app /app/uploads /app/knowledge
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"
CMD ["sh", "-c", "exec uvicorn \"$APP_MODULE\" --host 0.0.0.0 --port 8000 --workers \"$WEB_CONCURRENCY\" --no-proxy-headers --no-server-header"]
