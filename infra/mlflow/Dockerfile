# Local MLflow tracking server for the scoring / progress-estimation experiment loop.
# Pinned so every run logs against the same server build. Fully local; no account.
FROM python:3.12-slim

RUN pip install --no-cache-dir mlflow==2.18.0

EXPOSE 5000
