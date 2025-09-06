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
- [ ] etl-api: `/ingest/webhook` 구현
- [ ] worker: 첨부 다운로드 + 해시 검증
- [ ] 파서: PDF / XLSX / DOCX → 텍스트·표·범위
- [ ] 청킹: 350–450자, overlap 10–15%
- [ ] 임베딩: snowflake v2 ko, batch 32–64
- [ ] 업서트: Qdrant + SQLite 색인
- [ ] 메타: category/filetype/posted_at/severity

---

## 3. 검색/색인
- [ ] Qdrant 컬렉션 생성 (1024d, cosine, HNSW)
- [ ] SQLite FTS5 인덱스 (title/body/tags)
- [ ] Hybrid Search Adapter: BM25+Vector → RRF
- [ ] Rerank: bge-reranker-small (ONNX/CPU)
- [ ] 최신성 부스트(posted_at)

---

## 4. RAG 파이프라인
- [ ] rag-api: `/rag/query` (OpenAI-Compat)
- [ ] Table Mode: 엑셀 질문 라우팅
- [ ] Normal Mode: 상위 6–8 청크 합성
- [ ] Citations Formatter 적용
- [ ] PII/내부정보 거절/마스킹 규칙

---

## 5. UI
- [ ] 게시판 React UI: 글 작성/첨부
- [ ] Chatbot UI: 질문/답변/출처 탭
- [ ] 첨부 미리보기 (PDF page, XLSX range)
- [ ] 필터: 기간/카테고리/파일타입
- [ ] Feedback 버튼 (👍/👎)

---

## 6. 모델
- [ ] Ollama/llama.cpp 기동 (Gemma3 12B)
- [ ] 양자화: Q4_K_M (기본), Q5_K_M (고품질)
- [ ] 동시성: 12B(2–4), 27B(1–2)
- [ ] 스트리밍 SSE + 타임아웃 정책

---

## 7. Embedding
- [ ] Sentence-Transformers 서비스: snowflake v2 ko
- [ ] 출력 차원 1024 고정
- [ ] query/passages 템플릿 분리
- [ ] mean pooling + L2 normalize
- [ ] 캐시: 임베딩 해시 재사용
- [ ] Qdrant 컬렉션 스키마 반영

---

## 8. 평가 / LLM as a Judge
- [ ] 평가 데이터셋 3종 준비:
  - Master Set (정확도/관련성/가독성)
  - Refusal Set (정책 거절)
  - PII Exposure Set (개인정보 노출)
- [ ] eval-api 서비스 구현:
  - 입력: question, gold_answer?, policy_rule?
  - 출력: score_accuracy, score_relevance, score_readability, refusal?, pii_detected?
- [ ] 저지 모델 서빙:
  - 내부: Gemma3 7B/9B (판사용)
  - 외부 API: OpenAI/Anthropic 모델 (fallback)
- [ ] 리포트 산출: metrics_{date}.json|csv
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
