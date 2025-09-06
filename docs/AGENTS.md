# AGENTS.md

## 프로젝트 개요
- 이름: 그룹포털 게시판 RAG 챗봇 (MVP)
- 목적: 사내 게시판(본문 + 첨부)을 대상으로 검색 + RAG + Chatbot UI 기능 제공
- 데이터: 게시글 + 첨부 (PDF, XLSX, DOCX)
- 컨트롤 플레인: **Dify** (워크플로우/로그/앱 API, KB·업로드·프록시 OFF)

---

## 현재 상태 요약 (MVP)
- ETL: 웹훅(`/webhook`,`/ingest/webhook`) → 업로드(`/upload`) → 첨부 다운로드/파싱(PDF/XLSX/DOCX) → 청킹 → 임베딩 → Qdrant 업서트 → SQLite FTS5 색인(메타: posted_at, severity)
- 검색: Hybrid(BM25+Vector → RRF) + bge-reranker-small 재랭크 + 최신성 소폭 부스트 + 필터(기간/카테고리/파일타입)
- RAG: `/search/hybrid`, `/rag/query`, 스트리밍 `/rag/stream` + 정책(PII/내부정보) 거절/마스킹 + 피드백 로깅(`/feedback`)
- 임베딩: Sentence-Transformers 옵션(snowflake v2 ko), query/passages 템플릿 분리, Redis 캐시 재사용
- 모델: Gemma3 12B(Ollama) 기반, 양자화 태그 지원, 동시성 세마포어, 타임아웃, SSE 스트리밍
- UI: 게시판(Board) 글 작성/첨부 업로드, 챗봇(Chatbot) 질문/답변/출처 탭 + PDF page/XLSX range 미리보기 + 필터 + 👍/👎
- 평가: 데이터셋(master/refusal/pii), 저지 모델(Qwen2 32B) 통합, 리포트(metrics_*.json)

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
4. IR 색인(SQLite FTS5, 제목/본문/태그/카테고리/파일타입/posted_at/severity)
5. 검색 시: BM25 top-50 + Vec top-50 → RRF(kRR=60) → top-20 rerank + 최신성 부스트 + 선택적 필터
6. rag-api: LLM 합성 답변 + 출처(문서명 + 범위) + 정책 거절/마스킹 + 스트리밍(SSE)

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
- **서빙**: Ollama or llama.cpp server, OpenAI-Compat, SSE(`/rag/stream`)
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
  - 내부: Qwen2 32B(권장) 또는 Gemma3 27B (대안)
  - 외부 API: 사용 안 함

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
  ├─ search_adapter/ # IR+Vector RRF
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

---
## 문서 업데이트 규칙

- WBS.md와 AGENTS.md를 참고하여 기능구현할 것
- 기능구현 후 WBS.md에 기록하여 진척률 확인 및 README.md에 영향을 주는 기능구현이라면 내용반영할 것
