# Clara engine + API (Python). Default command runs the zero-dependency reference
# server (reference UI + API in one process). docker-compose overrides the command
# to run uvicorn as the API-only backend behind the Next frontend.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy metadata first so the dependency layer caches across source changes.
COPY pyproject.toml README.md ./
COPY clara ./clara
COPY api ./api
COPY web ./web

# api = FastAPI/uvicorn, ingest = HTML/PDF/DOCX, ru/es/de/fr = lemmatizers.
# (pdf/ocr extras need system libraries and are left out of the default image.)
RUN pip install ".[api,ingest,ru,es,de,fr]"

EXPOSE 8000

# Single-process default: serves the reference UI and the API on one port.
CMD ["python", "web/serve.py", "--host", "0.0.0.0", "--port", "8000"]
