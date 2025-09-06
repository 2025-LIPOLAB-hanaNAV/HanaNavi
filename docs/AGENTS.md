# AGENTS.md

## 프로젝트 개요
- 이름: 그룹포털 게시판 RAG 챗봇 (MVP)
- 목적: 사내 게시판(본문 + 첨부)을 대상으로 검색 + RAG + Chatbot UI 기능 제공
- 데이터: 게시글 + 첨부 (PDF, XLSX, DOCX)
- 컨트롤 플레인: **Dify** (워크플로우/로그/앱 API, KB·업로드·프록시 OFF)

---

## 주요 스택
- Backend: Python (FastAPI, Celery or Prefect)
- Vector DB: **Qdrant** (1024d, cosine)
- IR DB: SQLite FTS5 (MVP), 필요 시 Meilisearch 승격
- Cache/DB: Redis, Postgres (Dify 필수)
- Storage: 로컬 볼륨(첨부), 필요 시 MinIO 승격
- LLM: **Gemma3 12B** (상향 시 27B), Ollama/llama.cpp 내부 서빙
- Embedding: Sentence-Transformers  
  `dragonkue/snowflake-arctic-embed-l-v2.0-ko` (1024d, ko 특화)
- Rerank: bge-reranker-small (ONNX/CPU)
- UI: React (데모 게시판 + Chatbot UI), (옵션) Open WebUI Viewer Mode
- Infra: Docker Compose

---

## 데이터 파이프라인
1. 게시판 이벤트(Webhook) → `etl-api`
2. Worker: 첨부 다운로드 → 파싱(pdf/xlsx/docx) → 청킹
3. 임베딩(snowflake v2 ko) → Qdrant 업서트
4. IR 색인(SQLite FTS5, 제목/본문/태그/카테고리/파일타입/날짜)
5. 검색 시: BM25 top-50 + Vec top-50 → RRF(kRR=60) → top-20 rerank
6. rag-api: LLM 합성 답변 + 출처(문서명 + 페이지/시트:셀)

---

## RAG 워크플로우 (Dify)
- Input → Hybrid Search(HTTP `/search/hybrid`) → Rerank → Router(Table/Normal)
- Table Mode: 엑셀 질문 감지 → 범위 요약
- Normal: LLM 합성
- Output: 답변 + 출처(문서명 + 범위)
- Citations Formatter: 포맷 강제

---

## 모델 세부
- **LLM 주모델**: Gemma3 12B (Q4_K_M 기본, Q5_K_M 고품질)  
  - 동시성: 2–4 세션
- **옵션**: Gemma3 27B (동시성 1–2)  
- **서빙**: Ollama or llama.cpp server, OpenAI-Compat
- **임베딩**: snowflake v2 ko (1024d), mean pooling + L2 normalize
- **재랭크**: bge-reranker-small (ONNX/CPU)

---

## 평가 / LLM as a Judge
- **목적**: 응답 품질/정책 준수 자동 평가
- **판사 역할**:
  - 정확도 / 관련성 / 가독성
  - 출처 검증 (응답 vs 컨텍스트)
  - 거절/안전 정책 평가 (PII, 내부 민감정보)
- **데이터셋**:
  - Master Set (정확도·가독성)
  - Refusal Set (정책 거절)
  - PII Exposure Set (개인정보 노출)
- **운영**:
  - `eval-api` 서비스 → 배치 평가
  - 리포트: `reports/metrics_{date}.json|csv` (평균/분포, 실패 Top-N, 판사 불일치 목록)
- **저지 모델**:
  - 내부: Gemma3 7B/9B (경량판)
  - 외부 API: GPT-4o-mini / Claude Sonnet (fallback)

---

## 정책
- 출처 없는 문장 금지
- 각 주장 뒤 반드시 출처(문서명 + 페이지|시트:셀)
- 개인정보/내부정보 → 마스킹 또는 안내
- 평가 루프: Master/Refusal/PII dataset으로 정기 실행

---

## 폴더 구조 제안
```yaml
app/
  ├─ etl-api/        # FastAPI ingest
  ├─ worker/         # Celery/Prefect tasks
  ├─ parser/         # pdf/xlsx/docx 파서
  ├─ indexer/        # 색인 모듈
  ├─ rag-api/        # 검색+합성 API (OpenAI-Compat)
  ├─ search-adapter/ # IR+Vector RRF
  ├─ eval-api/       # LLM Judge 평가 서비스
  ├─ models/         # LLM/임베딩 초기화
  └─ utils/          # 공용 유틸리티

ui/
  ├─ board-react/    # 게시판 UI
  └─ chatbot-react/  # 챗봇 UI

docker/
  └─ docker-compose.yml

docs/
  ├─ AGENTS.md
  └─ WBS.md

reports/
  └─ metrics_*.json|csv
```

