# ===================================================================
# 1. 빌더 스테이지: 라이브러리를 설치하는 역할만 담당
# ===================================================================
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG OFFLINE=0

# 가상 환경 생성 및 경로 설정
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# requirements와 whl 파일 복사
COPY requirements/rag-api.txt /tmp/requirements.txt
RUN mkdir -p /wheels /wheels/common /wheels/rag-api
COPY vendor/wheels /wheels

# 기존과 동일한 로직으로 라이브러리 설치 (가상 환경 내에 설치됨)
RUN FL="--find-links=/wheels --find-links=/wheels/common --find-links=/wheels/rag-api"; \
    if [ "$OFFLINE" = "1" ] && ls -1 /wheels 2>/dev/null | grep -E '\.whl$' -q; then \
      pip install --no-cache-dir --no-index $FL -r /tmp/requirements.txt; \
    else \
      pip install --no-cache-dir $FL -r /tmp/requirements.txt; \
    fi


# ===================================================================
# 2. 최종 스테이지: 실제 애플리케이션을 실행하는 역할
# ===================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 빌더 스테이지에서 라이브러리가 설치된 가상 환경만 복사
# (whl 파일 등 빌드에만 사용된 파일들은 복사되지 않음)
COPY --from=builder /opt/venv /opt/venv

# 애플리케이션 코드 복사
WORKDIR /app
COPY app /app/app

# 가상 환경 활성화
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app/app/rag-api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]