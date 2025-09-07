FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

ARG OFFLINE=0

WORKDIR /app

COPY requirements/etl-api.txt /tmp/requirements.txt
RUN mkdir -p /wheels /wheels/common /wheels/etl-api
COPY vendor/wheels /wheels
RUN FL="--find-links=/wheels --find-links=/wheels/common --find-links=/wheels/etl-api"; \
    if [ "$OFFLINE" = "1" ] && ls -1 /wheels 2>/dev/null | grep -E '\.whl$' -q; then \
      pip install --no-cache-dir --no-index $FL -r /tmp/requirements.txt; \
    else \
      pip install --no-cache-dir $FL -r /tmp/requirements.txt; \
    fi

COPY app /app/app

WORKDIR /app/app/etl-api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
