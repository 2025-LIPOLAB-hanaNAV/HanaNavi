FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG OFFLINE=0

WORKDIR /app

COPY requirements/worker.txt /tmp/requirements.txt
# Optional wheelhouse for offline/fast installs
RUN mkdir -p /wheels
COPY vendor/wheels /wheels
RUN if [ "$OFFLINE" = "1" ]; then \
      pip install --no-cache-dir --no-index \
        --find-links=/wheels/common --find-links=/wheels/svc \
        -r /tmp/requirements.txt; \
    else \
      pip install --no-cache-dir \
        --find-links=/wheels/common --find-links=/wheels/svc \
        -r /tmp/requirements.txt; \
    fi

COPY app /app/app

WORKDIR /app

CMD ["celery", "-A", "app.worker.celery_app:app", "worker", "--loglevel=info"]
