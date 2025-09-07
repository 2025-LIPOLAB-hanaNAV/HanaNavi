FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

ARG OFFLINE=0

WORKDIR /app

COPY requirements/rag-api.txt /tmp/requirements.txt
# Optional wheelhouse (fallback to PyPI if empty and OFFLINE!=1)
COPY vendor/wheels/common /wheels/common
COPY vendor/wheels/rag-api /wheels/svc
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

WORKDIR /app/app/rag-api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
