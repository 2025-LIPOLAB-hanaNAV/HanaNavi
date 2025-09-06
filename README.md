# 그룹포털 게시판 RAG 챗봇 (MVP)

사내 게시판(본문 + 첨부파일)을 대상으로 **검색 + RAG + Chatbot UI** 기능을 제공하는 챗봇 프로젝트입니다.  
첨부파일(PDF, XLSX, DOCX)을 파싱하고, IR + Vector 하이브리드 검색 및 LLM 합성을 통해 **정확한 답변 + 출처**를 제공합니다.

---

## ✨ 주요 기능 (MVP)
- 게시판 + 첨부(Webhook 기반 수집)
- 첨부 파싱(PDF/XLSX/DOCX) 및 청킹
- 한국어 특화 임베딩: `dragonkue/snowflake-arctic-embed-l-v2.0-ko` (1024d)
- Qdrant(Vector) + SQLite FTS5(IR) → RRF 융합 검색
- LLM: Gemma3 12B (옵션 27B), Ollama/llama.cpp 내부 서빙
- Table Mode: 엑셀 질의 분기 (시트/셀 범위 인용)
- Chatbot UI (React) + 게시판 UI (React)
- LLM as a Judge (응답 품질/정책 자동 평가)

---

## 🏗️ 아키텍처 개요
```
[Board React] ──> [etl-api] ──> [worker] ──> Qdrant (Vector)
│ │ SQLite FTS5 (IR)
│ └─> MinIO/로컬 볼륨 (첨부)
│
[Chatbot React] ──> [rag-api] ──> [search-adapter] ──> Hybrid Search
│
└─> LLM (Gemma3 @ Ollama)
```

- Control Plane: **Dify** (워크플로우/로그/앱 API)  
- IR: SQLite FTS5 (→ 필요 시 Meilisearch 승격)  
- Vector: Qdrant  
- Storage: 로컬 볼륨 (→ MinIO 승격 가능)

---

## 📂 폴더 구조
```yaml
app/
  ├── etl-api/        # FastAPI ingest
  ├── worker/         # Celery/Prefect tasks
  ├── parser/         # pdf/xlsx/docx 파서
  ├── indexer/        # 색인 모듈
  ├── rag-api/        # 검색+합성 API (OpenAI-Compat)
  ├── search_adapter/ # IR+Vector RRF
  ├── eval-api/       # LLM Judge 평가 서비스
  ├── models/         # LLM/임베딩 초기화
  └── utils/          # 공용 유틸리티
ui/
  ├── board-react/    # 게시판 UI (글 작성/첨부 업로드)
  └── chatbot-react/  # 챗봇 UI (질문/답변/출처 + 첨부 미리보기)
docker/
  └── docker-compose.yml
docs/
  ├── AGENTS.md
  └── WBS.md
reports/
  └── metrics_*.json|csv
```


---

## 🚀 실행
1) 환경변수 템플릿 복사:

```bash
cp .env.example .env
```

2) 전체 스택 기동(Qdrant/Redis/Postgres + APIs/worker + UI):

```bash
make up
```

3) 모델 준비(Ollama 로컬 사용):

```bash
# 로컬 Ollama가 실행 중이어야 합니다 (11434). 모델 다운로드:
ollama pull gemma3:12b
# 또는
make pull-model

# Q5_K_M 등 태그 변경 시:
make pull-model MODEL=gemma3:12b-q5_K_M
```

4) 헬스체크:

- etl-api: http://localhost:8002/health
- rag-api: http://localhost:8001/health
- eval-api: http://localhost:8003/health

5) 웹훅 테스트(작업 큐에 태스크 등록):

```bash
curl -X POST http://localhost:8002/webhook \
  -H 'Content-Type: application/json' \
  -d '{"action":"post_created","post_id":123,"url":"https://example"}'
```

6) 검색/질의 API:

- 하이브리드 검색: `POST http://localhost:8001/search/hybrid` body `{ "query": "...", "top_k": 20 }`
- RAG 질의: `POST http://localhost:8001/rag/query` body `{ "query": "...", "top_k": 8 }`

임베딩 가속(옵션):

- Sentence-Transformers 기반 임베딩 사용 시 `.env`에 `USE_ST=1` 설정
- 모델: `EMBEDDING_MODEL=dragonkue/snowflake-arctic-embed-l-v2.0-ko` (기본)
 - 템플릿 분리: `EMBED_USE_TEMPLATE=1`, `EMBED_QUERY_PREFIX`, `EMBED_PASSAGE_PREFIX` (기본 `query: ` / `passage: `)
 - 캐시: `EMBED_CACHE=redis` + `REDIS_URL=redis://redis:6379/0`로 임베딩 재사용

재랭크(bge-reranker-small):

- 기본값: ST CrossEncoder 백엔드(`RERANK_BACKEND=st`)로 CPU 동작
- ONNX 사용 시: 모델 ONNX 파일을 볼륨에 두고 `RERANK_BACKEND=onnx`, `RERANKER_ONNX_PATH=/models/bge-reranker-small.onnx` 지정
- 가중치: `RERANK_ALPHA=0.7` (CE 점수 0.7 + RRF 0.3)

정책 엔포스먼트(PII/내부정보):

- 기본 활성화: `/rag/query` 요청에서 `enforce_policy: true` (기본값)
- 거절 규칙: 질의가 전화/이메일/주민등록/계좌 등 PII를 요구하면 거절 응답
- 마스킹 규칙: 답변 내 이메일/전화/주민등록/카드/API 키 등 패턴 자동 마스킹
- 응답 필드: `policy.refusal`, `policy.masked`, `policy.pii_types`, `policy.reason`

---

## 🐳 Docker Quickstart (요약)

- 사전 준비: Docker(Compose v2), 포트 사용 가능: 11434, 6333, 6379, 5432, 8001/2/3, 5173/5174, 9000/9001
- 1) 기동: `make up`
- 2) 모델 풀(태그 변경): `make pull-model MODEL=gemma3:12b-q5_K_M`
- 3) UI 접속: Board `http://localhost:5173`, Chatbot `http://localhost:5174`
- 4) 업로드 예시:
  ```bash
  curl -F file=@README.md http://localhost:8002/upload
  ```
- 5) 웹훅(색인) 예시:
  ```bash
  curl -X POST http://localhost:8002/ingest/webhook \
    -H 'Content-Type: application/json' \
    -d '{"action":"post_created","post_id":1001,"title":"보이스피싱 주의","body":"사칭 주의 공지","attachments":[{"filename":"README.md","url":"http://etl-api:8000/files/README.md"}],"date":"2025-09-06","category":"Notice"}'
  ```
- 6) 하이브리드 검색:
  ```bash
  curl -s http://localhost:8001/search/hybrid -H 'Content-Type: application/json' \
    -d '{"query":"보이스피싱 대응 절차"}' | jq .
  ```
- 7) RAG 질의:
  ```bash
  curl -s http://localhost:8001/rag/query -H 'Content-Type: application/json' \
    -d '{"query":"보이스피싱 의심 전화 대응"}' | jq .
  ```
- 8) 스트리밍(SSE):
  ```bash
  curl -N http://localhost:8001/rag/stream \
    -H 'Content-Type: application/json' \
    -d '{"query":"계좌 지급정지 절차"}'
  ```
- 9) 평가 실행:
  ```bash
  curl -s http://localhost:8003/eval/run -H 'Content-Type: application/json' -d '{"dataset":"master"}' | jq .
  # 브라우저로 리포트 확인
  # macOS: open http://localhost:8003/reports
  # Windows: start http://localhost:8003/reports
  ```
- 10) 종료/로그:
  - 종료: `make down`
  - 전체 로그: `make logs`
  - 특정 서비스 로그: `docker compose -f docker/docker-compose.yml logs -f rag-api`

환경 변수는 `.env.example` 참고 후 `.env`에 설정하세요. 로컬 Python/Node 설치 없이 Docker만으로 실행 가능합니다.

참고: 컨테이너에서 로컬 Ollama에 연결하려면 `.env`의 `OLLAMA_BASE_URL`을 `http://host.docker.internal:11434`로 둡니다. Linux에서도 `host.docker.internal`이 동작하도록 compose에 host-gateway 매핑이 포함되어 있습니다.

---

## 📊 평가 (LLM as a Judge)
- 데이터셋: `datasets/master/voice_phishing_master_ko.jsonl`, `datasets/refusal/refusal_ko.jsonl`, `datasets/pii/pii_exposure_ko.jsonl`
- 저지 모델: 기본 Qwen2 32B (Ollama), 대안 Gemma3 27B
- 실행:
  - `POST http://localhost:8003/eval/run` body `{ "dataset": "master|refusal|pii" }`
  - 리포트: `docker/appdata` 볼륨의 `/data/reports/metrics_*.json`
- 품질 지표: 정확도, 관련성, 가독성, 거절률, PII 탐지율

---

## 🛠️ 개발 진행 상황
- [x] AGENTS.md / WBS.md 정리 및 유지
- [x] ETL: 웹훅 → 다운로드 → 파싱(PDF/XLSX/DOCX) → 청킹 → 임베딩 → Qdrant 업서트 → SQLite 색인
- [x] 검색: Hybrid(BM25+Vector → RRF) + bge-reranker-small 재랭크 + 최신성 부스트
- [x] RAG API: `/search/hybrid`, `/rag/query`, 스트리밍 `/rag/stream` + 정책(PII/내부정보) 엔포스먼트 + 피드백 로깅
- [x] 임베딩: ST 옵션(snowflake v2 ko), query/passages 템플릿 분리, Redis 캐시
- [x] 모델: Ollama Gemma3 12B(양자화 태그 지원), 동시성 세마포어, 타임아웃
- [x] UI: 게시판 업로드(Board) + 챗봇(Chatbot) 탭/필터/첨부 미리보기(PDF page, XLSX range)
- [x] 평가: 데이터셋(master/refusal/pii), 저지 모델(Qwen2 32B) 통합, 리포트 산출
- [ ] 운영: 정기 실행(주간) 배치 및 대시보드

개발 진행에 따라 README를 지속 업데이트합니다.
게시판 UI 실행:

- Docker: `docker compose -f docker/docker-compose.yml up -d board`
- 브라우저에서 http://localhost:5173 접속 → 글 작성/첨부 업로드 → etl-api 연동

챗봇 UI 실행:

- Docker: `docker compose -f docker/docker-compose.yml up -d chatbot`
- 브라우저에서 http://localhost:5174 접속 → 질문 입력 → 답변/출처 확인 → '미리보기'로 첨부 확인(PDF 임베드)

모델 설정

- 서비스: `ollama` 컨테이너에서 로컬 LLM 서빙(OpenAI 호환은 선택)
- 모델 선택: `.env`에 `LLM_MODEL` 지정(기본 `gemma3:12b`)
- 동시성: `.env`에 `LLM_MAX_SESSIONS`로 제한(12B: 2–4 권장, 27B: 1–2 권장)
- 타임아웃: `.env`에 `LLM_TIMEOUT`(초) 설정
- 스트리밍: `POST /rag/stream` SSE 엔드포인트 제공
- OpenAI-Compat 사용 시: `.env`에 `LLM_API=openai`와 `OLLAMA_BASE_URL`을 해당 호환 서버 주소로 설정
