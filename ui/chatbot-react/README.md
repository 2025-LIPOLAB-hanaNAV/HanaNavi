HanaNavi Chatbot (React)

- 스트리밍(SSE) 기반 RAG 챗봇 UI입니다.
- 하이브리드 검색 + 인용 표시, 정책 정보(거절/마스킹) 표시는 API 응답을 그대로 사용합니다.
- 로컬 Ollama 모델 관리(목록/풀) UI가 포함됩니다.

기본 동작

- 백엔드 `rag-api` 엔드포인트와 통신합니다.
  - 질의 스트리밍: `POST {RAG_BASE}/rag/stream` (SSE)
  - 모델 목록: `GET {RAG_BASE}/llm/models`
  - 모델 풀: `POST {RAG_BASE}/llm/pull` (Ollama)
- 보드/첨부 링크는 각각 `board-react`, `etl-api` 주소를 기반으로 열립니다.

환경 변수 (Vite)

- `VITE_RAG_BASE` (기본 `http://localhost:8001`): rag-api 베이스 URL
- `VITE_ETL_BASE` (기본 `http://localhost:8002`): etl-api 베이스 URL (첨부 링크)
- `VITE_BOARD_BASE` (기본 `http://localhost:5173`): 게시판 UI 주소 (게시글 링크)

주요 기능

- 메시지 스트리밍 표시, 중지 버튼
- 인용 패널(답변별 인용 목록, 게시글/첨부 링크)
- 모델 관리: 목록 갱신, 모델명 입력 후 Pull, 선택한 모델 로컬 스토리지 저장
- 간단한 오류 표시 및 상태 표시(로딩/스트리밍)

로컬 개발

1) 루트에서 전체 스택 실행: `make up`
2) 단독 실행도 가능: 이 디렉터리에서 `npm i && npm run dev` (포트 5174)
   - .env.local 등에 `VITE_RAG_BASE` 등을 설정하거나 기본값을 사용합니다.

Docker 빌드/런

- 루트에서 UI만 빌드: `make build-ui`
- 컨테이너 기동: `docker compose -f docker/docker-compose.yml up -d chatbot`

비고

- 모델 풀은 `LLM_API=ollama`일 때만 의미가 있습니다.
- 서버가 인용을 제공하지 않거나 정책 거절인 경우, 인용 패널은 비어 있을 수 있습니다.
