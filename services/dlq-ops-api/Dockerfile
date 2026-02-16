FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY libs/shared /app/libs/shared
COPY services/dlq-ops-api /app/services/dlq-ops-api

RUN pip install --no-cache-dir -e /app/libs/shared \
    && pip install --no-cache-dir -r /app/services/dlq-ops-api/requirements.txt

WORKDIR /app/services/dlq-ops-api
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
