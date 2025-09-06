# WBS - 그룹포털 게시판 RAG 챗봇 (MVP, Slim Profile)

컨트롤 플레인: **Dify**  
Vector DB: **Qdrant 고정**  
IR: SQLite FTS5 (→ Meilisearch 승격 가능)  
LLM: Gemma3 12B (→ 27B 상향)  
Embedding: snowflake-arctic-embed-l-v2.0-ko (1024d)

---

## 0. 결정/정책
- [x] Control = Dify (KB/업로드/프록시 OFF)
- [x] Vector = Qdrant (1024d, cosine)
- [x] IR = SQLite FTS5 (필요 시 Meili 승격)
- [x] Storage = 로컬 볼륨 (→ MinIO 승격)
- [x] LLM = Gemma3 12B (27B 옵션), Ollama/llama.cpp
- [x] Embedding = snowflake v2 ko (1024d)

---

## 1. 기획/계약
- [x] 요구사항/핵심기능 합의
- [x] 데이터 계약 문서화 (Webhook/Chunk/Index/Query)
- [ ] 출처 규약 고정 (문서명 + 페이지|시트:셀)

---

## 2. ETL
- [x] etl-api: `/ingest/webhook` 구현 (alias `/webhook`)
- [x] worker: 첨부 다운로드 + 해시 검증(SHA1)
- [x] 파서: PDF / XLSX / DOCX → 텍스트·표·범위(MVP)
- [x] 청킹: 350–450자(기본 400), overlap 10–15%(기본 12.5%)
- [x] 임베딩: snowflake v2 ko (Sentence-Transformers, `USE_ST=1` 옵션), batch 32
- [x] 업서트: Qdrant + SQLite 색인
- [x] 메타: category/filetype/posted_at/severity 반영

---

## 3. 검색/색인
- [x] Qdrant 컬렉션 생성 (1024d, cosine, HNSW)
- [x] SQLite FTS5 인덱스 (title/body/tags)
- [x] Hybrid Search Adapter: BM25+Vector → RRF (MVP)
- [x] Rerank: bge-reranker-small (ONNX/CPU, ST fallback)
- [x] 최신성 부스트(posted_at) 소규모 가중치 적용

---

## 4. RAG 파이프라인
- [x] rag-api: `/rag/query` (OpenAI-Compat 스타일 JSON)
- [x] Table Mode: 엑셀 질문 라우팅(간단 히유리스틱)
- [x] Normal Mode: 상위 6–8 청크 합성
- [x] Citations Formatter 적용(문서명+chunk id 기반)
- [x] PII/내부정보 거절/마스킹 규칙 (정책 엔포스먼트)

---

## 5. UI
- [x] 게시판 React UI: 글 작성/첨부 (MVP 업로드→웹훅 연동)
- Chatbot UI
  - [x] 질문/답변/출처
  - [x] 탭 분리(질문/답변/출처)
  - [x] 첨부 미리보기(PDF page, XLSX range)
  - [x] 필터: 기간/카테고리/파일타입
  - [x] Feedback 버튼 (👍/👎)

---

## 6. 모델
- [x] Ollama/llama.cpp 기동 (Gemma3 12B) — docker-compose `ollama` 서비스, Make `pull-model`
- [x] 양자화: Q4_K_M(기본), Q5_K_M(옵션) — Make `MODEL=` 파라미터 및 README 가이드
- [x] 동시성: 12B(2–4), 27B(1–2) — `LLM_MAX_SESSIONS` 세마포어로 제한
- [x] 스트리밍 SSE + 타임아웃 정책 — `/rag/stream` SSE, `LLM_TIMEOUT`

---

## 7. Embedding
- [x] Sentence-Transformers 서비스: snowflake v2 ko (옵션)
- [x] 출력 차원 1024 고정
- [x] query/passages 템플릿 분리 (환경변수 프리픽스)
- [x] mean pooling + L2 normalize
- [x] 캐시: 임베딩 해시 재사용(옵션 Redis)
- [x] Qdrant 컬렉션 스키마 반영

---

## 8. 평가 / LLM as a Judge
- [ ] 평가 데이터셋 3종 준비:
  - Master Set (정확도/관련성/가독성)
  - Refusal Set (정책 거절)
  - PII Exposure Set (개인정보 노출)
- [x] eval-api 서비스 구현(베이직):
  - 입력: question, gold_answer?, policy_rule?
  - 출력: placeholder metrics 파일 기록(`reports/metrics_*.json`)
- [ ] 저지 모델 서빙:
  - 내부: Gemma3 7B/9B (판사용)
  - 외부 API: OpenAI/Anthropic 모델 (fallback)
- [x] 리포트 산출: metrics_{date}.json (MVP)
  - 평균/분포, 실패 Top-N, 판사 불일치 목록
- [ ] 정기 실행(주간), 대시보드 업데이트

---

## 9. 운영/평가 루프
- [ ] Eval 20문항 (일정/요건/표질의 포함)
- [ ] 자동 평가: 정답 포함률/환각률/출처 정확성
- [ ] 리포트 산출(JSON/CSV)
- [ ] 주간 리소스/지연 모니터링

---

## 10. 인프라
- [ ] docker-compose: mem_limit (서비스별 512m~2g)
- [ ] Postgres/Redis/Qdrant/SQLite/MinIO 세팅
- [ ] 로그/메트릭 기본 구조화
