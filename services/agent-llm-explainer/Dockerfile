FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY libs/shared /app/libs/shared
COPY services/agent-llm-explainer /app/services/agent-llm-explainer

RUN pip install --no-cache-dir -e /app/libs/shared \
    && pip install --no-cache-dir -r /app/services/agent-llm-explainer/requirements.txt

WORKDIR /app/services/agent-llm-explainer
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
