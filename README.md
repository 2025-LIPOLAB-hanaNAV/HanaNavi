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

2) 전체 스택 기동(Qdrant/Redis/Postgres/Ollama + APIs/worker):

```bash
make up
```

3) 처음 한 번 Gemma3 모델 다운로드(Ollama):

```bash
make pull-model
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

## 📊 평가 (LLM as a Judge)
- Master Set / Refusal Set / PII Exposure Set 평가
- 자동 리포트: `reports/metrics_{date}.json|csv`
- 품질 지표: 정확도, 출처 정확성, 환각률, 거절율

---

## 🛠️ 개발 진행 상황
- [x] AGENTS.md / WBS.md 작성
- [ ] ETL 파이프라인 초기 구현
- [ ] Hybrid Search Adapter
- [ ] RAG API + LLM 연결
- [ ] React UI (Board/Chatbot)
- [ ] 평가 루프 구축

개발 진행에 따라 README를 지속 업데이트합니다.
게시판 UI 실행:

- Docker: `docker compose -f docker/docker-compose.yml up -d board`
- 브라우저에서 http://localhost:5173 접속 → 글 작성/첨부 업로드 → etl-api 연동

챗봇 UI 실행:

- Docker: `docker compose -f docker/docker-compose.yml up -d chatbot`
- 브라우저에서 http://localhost:5174 접속 → 질문 입력 → 답변/출처 확인 → '미리보기'로 첨부 확인(PDF 임베드)
