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
  ├── board-react/    # 게시판 UI (글 작성/수정/삭제/첨부 업로드, DB 연동)
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

2) 전체 스택 기동(Qdrant/Redis/Postgres/Ollama + APIs/worker + UI):

```bash
make up
```

3) 모델 준비(Ollama 도커 사용/오프라인 반입):

```bash
# 컨테이너 안에서 모델 다운로드:
make pull-model

# Q5_K_M 등 태그 변경:
make pull-model MODEL=gemma3:12b-q5_K_M

# (옵션) 오프라인 반입: 다른 머신의 ~/.ollama를 서버로 복사한 뒤
# .env의 OLLAMA_MODELS_HOST_DIR를 해당 경로로 설정하면 컨테이너에 마운트되어 즉시 사용 가능
```

4) 헬스체크:

- etl-api: http://localhost:8002/health
- rag-api: http://localhost:8001/health
- eval-api: http://localhost:8003/health

5) 게시판/웹훅 테스트(작업 큐에 태스크 등록):

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
- (옵션) OpenSearch 사용: `docker compose -f docker/docker-compose.yml --profile opensearch up -d opensearch opensearch-dashboards`
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
- 10) 종료/로그/빠른 재시도:
  - 종료: `make down`
  - 전체 로그: `make logs`
  - 특정 서비스 로그: `docker compose -f docker/docker-compose.yml logs -f rag-api`
  - 빠른 재빌드 팁:
    - 전체 빌드 캐시 사용: `make build` (기본 캐시 활용)
    - UI만 빌드: `make build-ui` → `docker compose -f docker/docker-compose.yml up -d board chatbot`
    - API만 빌드: `make build-apis` → `docker compose -f docker/docker-compose.yml up -d rag-api etl-api eval-api`
    - 실패 후 재시도 시: `make up` (재빌드 없이 기동), 필요 서비스만 `make up-rag` 등으로 부분 재기동
    - 완전 재빌드가 필요할 때만: `make rebuild`

환경 변수는 `.env.example` 참고 후 `.env`에 설정하세요. 로컬 Python/Node 설치 없이 Docker만으로 실행 가능합니다.

참고: 컨테이너에서 로컬 Ollama에 연결하려면 `.env`의 `OLLAMA_BASE_URL`을 `http://host.docker.internal:11434`로 둡니다. Linux에서도 `host.docker.internal`이 동작하도록 compose에 host-gateway 매핑이 포함되어 있습니다.

OpenSearch IR 백엔드

- 기본 IR은 SQLite FTS5이며, 대규모 데이터/고급 검색이 필요할 때 OpenSearch를 사용할 수 있습니다.
- 활성화(업그레이드 단계):
  1) `.env`에 `IR_BACKEND=opensearch` 설정
  2) OpenSearch(Nori 포함) 빌드/기동:
     - 빌드: `docker compose -f docker/docker-compose.yml --profile opensearch build opensearch`
     - 기동: `docker compose -f docker/docker-compose.yml --profile opensearch up -d opensearch`
  3) (옵션) 대시보드: `--profile opensearch up -d opensearch-dashboards` (http://localhost:5601)
  4) 서비스 재시작: `make restart service=worker` && `make restart service=rag-api`
  5) (선택) 기존 문서 재색인: `make reindex-opensearch`
- 인덱싱: worker가 ingest 시 `posts` 인덱스에 문서를 업서트합니다.
- 검색: rag-api가 BM25(IR)를 OpenSearch로, 벡터는 Qdrant로 질의 후 RRF 융합 → 재랭크
- 한국어 형태소 분석기(Nori): 기본 이미지는 포함하지 않습니다. 필요 시 OpenSearch 이미지를 커스터마이즈하여 `analysis-nori` 플러그인을 설치한 후 인덱스 매핑에 적용하세요(추후 프로파일 제공 가능).

게시판(Board) API/DB 연동

- board-api: FastAPI + SQLAlchemy(Postgres) 기반 CRUD 제공
  - 엔드포인트:
    - `GET /health`
    - `GET /posts?page=&page_size=&q=` 목록
    - `GET /posts/{id}` 상세
    - `POST /posts` 생성(첨부 메타 포함), 생성 시 etl-api에 웹훅 전달 → 색인
    - `PUT /posts/{id}` 수정, 수정 시 웹훅 → 재색인
    - `DELETE /posts/{id}` 삭제, 삭제 시 웹훅 → Qdrant/SQLite/OpenSearch에서 삭제
- UI(board-react)는 첨부는 `etl-api:/upload`로 업로드 후 반환된 메타를 `board-api:/posts`에 전달하여 저장합니다.
- 영속성:
  - 게시글/첨부 메타: Postgres `dify` DB 내 테이블(`board_posts`, `board_attachments`)
  - 첨부 파일: etl-api 컨테이너의 `/data/storage/uploads` (Compose `appdata` 볼륨) → 재기동 후에도 유지
- OpenSearch 연동:
  - `.env`에서 `IR_BACKEND=opensearch` 또는 `IR_DUAL=1` 설정 시 worker가 OpenSearch에도 upsert/delete 수행
  - 본 리포지토리는 `docker/opensearch/Dockerfile`로 Nori 플러그인을 포함한 이미지를 제공합니다.
  - 인덱스 매핑은 한글 분석기(ko_analyzer)가 title/body에 적용되도록 자동 생성됩니다(최초 생성 시).
 - 보안 플러그인 비밀번호(필수): 2.12+부터 OpenSearch는 최초 실행 시 `OPENSEARCH_INITIAL_ADMIN_PASSWORD`가 필요합니다.
   - `.env`에 설정(예: `OPENSEARCH_INITIAL_ADMIN_PASSWORD=admin123!`)
   - 클라이언트(rag-api/worker)는 `.env`의 `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`, `OPENSEARCH_URL=https://...`을 사용합니다.

## ⚡ 빠른 재빌드: 휠(whl) 사전 다운로드

대형 패키지(onnxruntime, transformers 등) 다운로드 시간을 줄이기 위해, 컨테이너 빌드 전에 whl을 미리 받아 로컬 캐시를 사용할 수 있습니다.

- 휠 다운로드(전 서비스):
  - `make wheels-all`
- 개별 서비스:
  - `make wheels-worker`, `make wheels-rag`, `make wheels-etl`, `make wheels-eval`
- 오프라인/캐시 설치 빌드:
  - `make build-apis-offline`

동작 원리
- `vendor/wheels/<service>`에 미리 whl을 내려받고, Dockerfile에서 `/wheels`를 `--find-links`로 참조하여 pip 설치를 수행합니다.
- `OFFLINE=1` 빌드 인자 사용 시 `--no-index`로 PyPI 접속 없이 로컬 wheelhouse만 사용합니다.

주의
- 일부 패키지는 바이너리 휠이 없어 sdist만 배포될 수 있습니다. 이 경우 `make wheels-*`에서 에러가 나도 무시되며, 빌드 시 PyPI에서 받거나(OFFLINE=0) 수동으로 휠을 추가해 주셔야 합니다.

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

모델 설정 / 관리

- 서비스: `ollama` 컨테이너에서 로컬 LLM 서빙(OpenAI 호환은 선택)
- 기본 모델: `.env`에 `LLM_MODEL` 지정(기본 `gemma3:12b`)
- UI에서 모델 선택: 챗봇 상단의 모델 셀렉터에서 현재 설치된 모델 목록을 조회/선택할 수 있습니다.
- 모델 Pull: 챗봇 상단 입력에 모델명(예:`qwen2:7b`) 입력 후 Pull 버튼으로 서버에 다운로드를 요청합니다.
  - 서버 API: `GET /llm/models`(설치 목록), `POST /llm/pull` body `{"model":"qwen2:7b"}` (Ollama 전용)
- 동시성: `.env`에 `LLM_MAX_SESSIONS`로 제한(12B: 2–4 권장, 27B: 1–2 권장)
- 타임아웃: `.env`에 `LLM_TIMEOUT`(초) 설정
- 스트리밍: `POST /rag/stream` SSE 엔드포인트 제공
- OpenAI-Compat(Dify 등) 사용 시:
  - `.env`: `LLM_API=openai`, `LLM_BASE_URL=http://<dify-host>:<port>`, `OPENAI_API_KEY=app-xxx`
  - 모델 목록/풀은 제공되지 않으며, UI에서 임의 모델명을 입력해 사용 가능합니다.
