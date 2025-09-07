FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG OFFLINE=0

WORKDIR /app

COPY requirements/worker.txt /tmp/requirements.txt
# Optional wheelhouse for offline/fast installs
RUN mkdir -p /wheels /wheels/common /wheels/worker
COPY vendor/wheels /wheels
RUN FL="--find-links=/wheels --find-links=/wheels/common --find-links=/wheels/worker"; \
    if [ "$OFFLINE" = "1" ] && ls -1 /wheels 2>/dev/null | grep -E '\.whl$' -q; then \
      pip install --no-cache-dir --no-index $FL -r /tmp/requirements.txt; \
    else \
      pip install --no-cache-dir $FL -r /tmp/requirements.txt; \
    fi

COPY app /app/app

WORKDIR /app

CMD ["celery", "-A", "app.worker.celery_app:app", "worker", "--loglevel=info"]
