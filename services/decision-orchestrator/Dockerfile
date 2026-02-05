FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY libs/shared /app/libs/shared
COPY services/decision-orchestrator /app/services/decision-orchestrator

RUN pip install --no-cache-dir -e /app/libs/shared \
    && pip install --no-cache-dir -r /app/services/decision-orchestrator/requirements.txt

WORKDIR /app/services/decision-orchestrator
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
