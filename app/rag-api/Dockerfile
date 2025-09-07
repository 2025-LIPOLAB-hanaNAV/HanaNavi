FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

ARG OFFLINE=0

WORKDIR /app

COPY requirements/rag-api.txt /tmp/requirements.txt
# Optional wheelhouse (fallback to PyPI if empty and OFFLINE!=1)
RUN mkdir -p /wheels /wheels/common /wheels/rag-api
COPY vendor/wheels /wheels
RUN FL="--find-links=/wheels --find-links=/wheels/common --find-links=/wheels/rag-api"; \
    if [ "$OFFLINE" = "1" ] && ls -1 /wheels 2>/dev/null | grep -E '\.whl$' -q; then \
      pip install --no-cache-dir --no-index $FL -r /tmp/requirements.txt; \
    else \
      pip install --no-cache-dir $FL -r /tmp/requirements.txt; \
    fi

COPY app /app/app

WORKDIR /app/app/rag-api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
