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
  ├── search-adapter/ # IR+Vector RRF
  ├── eval-api/       # LLM Judge 평가 서비스
  ├── models/         # LLM/임베딩 초기화
  └── utils/          # 공용 유틸리티
ui/
  ├── board-react/    # 게시판 UI
  └── chatbot-react/  # 챗봇 UI
docker/
  └── docker-compose.yml
docs/
  ├── AGENTS.md
  └── WBS.md
reports/
  └── metrics_*.json|csv
```


---

## 🚀 실행 (예정)
개발 중입니다. 실행 방법은 점진적으로 업데이트될 예정입니다.

예상 플로우:
1. `docker-compose up` 으로 Postgres, Redis, Qdrant, Dify 기동
2. `etl-api`와 `worker` 실행 → 게시판 이벤트 처리
3. `rag-api` 실행 → `/rag/query` 엔드포인트 제공
4. UI(React) 실행 → Chatbot/Board 인터페이스 제공

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
