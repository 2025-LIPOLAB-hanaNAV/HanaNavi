# 변경사항 (Changelog)

프로젝트의 주요 변경사항을 요약합니다. 태그 `v0.1.0` 이후의 주요 변경을 정리했습니다.

## v0.2.2

- 수정: `app/worker/pipeline.py`의 `IndentationError` 해결
- 수정: `app/board-api/main.py`의 `ImportError` 해결

## v0.2.1

- 수정: worker 파이프라인(OpenSearch 선택적 임포트) 들여쓰기 오류 수정 → Celery 기동 오류(IndentationError) 해소
- 문서: Chatbot UI README 갱신(스트리밍, 인용 패널, 모델 관리, 환경변수)
- 문서: README에 Chatbot UI 안내 링크 추가(경량)

## v0.2.0

- 추가: OpenSearch IR 백엔드(옵션) 지원 및 Nori 분석기 통합
  - `docker/opensearch/Dockerfile`(analysis-nori) 추가, Compose `--profile opensearch`
  - Worker/RAG: `IR_BACKEND=opensearch` 시 OpenSearch BM25 사용, 기본은 SQLite FTS5
  - 재색인 도구: `app.tools.reindex_opensearch`, Make `reindex-opensearch`
  - 유의어 사전: `config/opensearch/ko_synonyms.txt` + `app.tools.setup_opensearch`, Make `opensearch-setup`
- 추가: LLM 모델 관리
  - RAG API: `/llm/models`, `/llm/pull`, 요청별 `model` 지정
  - Chatbot UI: 모델 선택/목록 새로고침/모델 풀 기능
- 추가: Seed 스크립트(`make seed-sample`)로 예시 게시글 생성(보이스피싱 안내)
- 개선: 하이브리드 검색 + 재랭크 품질
  - OpenSearch `multi_match` 튜닝(fuzziness/phrase_prefix), RRF→재랭크 파이프라인 정돈
  - 최신성(posted_at) 소폭 가중치 적용
- 개선: 인용(Citations)
  - IR 결과 링크 정합성 개선, 소형 대화(smalltalk) 시 검색/인용 스킵
- 개선: 다중 턴(Chat) 지원
  - RAG 요청에서 최근 히스토리 포함하여 문맥 유지
- 개선: SSE/CORS 안정성
  - 와일드카드 Origin 호환, 멀티라인 SSE 파싱 개선
- 개선: UI 전반(보드/챗봇)
  - Tailwind 적용, 라우터 구성, 업로드/목록/상세/다운로드 UX 개선
  - 챗봇 스트리밍, 마크다운 렌더링, 출처 패널, 필터(기간/카테고리/파일타입)
- 개선: 빌드/운영 편의
  - Docker 빌드 캐시 최적화 및 Make 타겟 분리(build/build-apis/build-ui/rebuild)
  - Ollama GPU 지원(NVIDIA, cublas), 외부 Ollama 연동 옵션, 모델 오프라인 반입 가이드
- 안정화: Qdrant 컬렉션 미존재 시 예외 처리(BM25-only 폴백)
- 수정: Celery 태스크 임포트, Compose 파서 호환, Vite 플러그인 누락 등 자잘한 빌드/런타임 이슈
- 문서: README/AGENTS/WBS 갱신(OpenSearch 활성화/모델 관리/퀵스타트/운영 가이드)

- 추가: 게시판 DB/CRUD 완성 (Postgres)
  - board-api(FastAPI+SQLAlchemy) 신설: `GET/POST/PUT/DELETE /posts`
  - UI(board-react) 로컬스토리지 제거 → board-api 연동, 수정/삭제 지원
  - 첨부: etl-api `/upload`로 업로드 → board-api에 메타 저장 → 재시작 후에도 유지
- 추가: 삭제 파이프라인
  - worker: `post_deleted` 이벤트 처리 → Qdrant/SQLite/OpenSearch에서 삭제

참고: 자세한 커밋 내역은 `git log v0.1.0..HEAD --oneline`을 확인하세요.