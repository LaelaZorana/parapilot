# ParaPilot — runs fully offline on the deterministic stub provider.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PARAPILOT_PROVIDER=stub \
    PARAPILOT_DB_URL=sqlite:////data/parapilot.db

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App + bundled offline seed corpus.
COPY app ./app
COPY data ./data
COPY pyproject.toml README.md ./

# Writable volume for the SQLite progress DB.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# Container healthcheck hits the app's own health endpoint.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
