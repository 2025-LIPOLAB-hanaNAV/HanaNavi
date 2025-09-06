from typing import List, Dict, Any
import asyncio
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.search_adapter.hybrid import hybrid_search as do_hybrid
from app.models.llm_client import LLMClient
from app.utils.policy import enforce_policy
import os
import json
from datetime import datetime


class SearchRequest(BaseModel):
    query: str
    top_k: int = 20
    filters: Dict[str, Any] | None = None


class SearchResult(BaseModel):
    id: str
    score: float
    snippet: str
    source: str  # document name + page/sheet:cell
    post_id: str | None = None


class SearchResponse(BaseModel):
    results: List[SearchResult]


app = FastAPI(title="rag-api", version="0.1.0")

# CORS for Chatbot UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Wildcard works only when credentials are disabled
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
try:
    from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

    REQ_COUNTER = Counter("rag_requests_total", "Total requests", ["path"])  # type: ignore

    @app.middleware("http")
    async def _metrics_middleware(request, call_next):  # type: ignore
        response = await call_next(request)
        try:
            REQ_COUNTER.labels(path=request.url.path).inc()  # type: ignore
        except Exception:
            pass
        return response

    @app.get("/metrics")
    def metrics():  # type: ignore
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
except Exception:
    pass

# LLM concurrency limits
import os as _os
_max_sessions = int(_os.getenv("LLM_MAX_SESSIONS", "4"))
_llm_sem_async = asyncio.Semaphore(_max_sessions)
_llm_sem_thread = threading.BoundedSemaphore(_max_sessions)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/search/hybrid", response_model=SearchResponse)
def hybrid_search(req: SearchRequest) -> SearchResponse:
    rows = do_hybrid(req.query, top_k=req.top_k, filters=req.filters or {})
    results = [
        SearchResult(
            id=r["id"],
            score=r["score"],
            snippet=r.get("snippet", ""),
            source=r.get("source", ""),
            post_id=r.get("post_id"),
        )
        for r in rows
    ]
    return SearchResponse(results=results)


class RagRequest(BaseModel):
    query: str
    top_k: int = 8
    mode: str = "auto"  # auto|table|normal
    enforce_policy: bool = True
    filters: Dict[str, Any] | None = None


class RagResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    policy: Dict[str, Any]


def _detect_table_mode(q: str) -> bool:
    ql = q.lower()
    keywords = ["excel", "xlsx", "표", "시트", "셀", "range", "sheet"]
    return any(k in ql for k in keywords)


@app.post("/rag/query", response_model=RagResponse)
def rag_query(req: RagRequest) -> RagResponse:
    mode = req.mode
    if mode == "auto":
        mode = "table" if _detect_table_mode(req.query) else "normal"

    hits = do_hybrid(req.query, top_k=max(10, req.top_k), filters=req.filters or {})
    ctx = "\n\n".join([f"[{i+1}] {h['snippet']}" for i, h in enumerate(hits[: req.top_k])])
    cits = [
        {
            "id": h["id"],
            "title": h.get("title"),
            "source": h.get("source"),
            "post_id": h.get("post_id"),
        }
        for h in hits[: req.top_k]
    ]

    # Compose prompt (LLM stubbed for now)
    client = LLMClient()
    prompt = (
        "질의에 답하세요. 각 주장 뒤에 반드시 [n] 인용 번호를 붙이세요.\n"
        "인용은 아래 컨텍스트에서만 선택하세요.\n\n"
        f"질의: {req.query}\n\n컨텍스트:\n{ctx}\n\n"
        "출력: 답변 본문과 마지막 줄에 'Citations: [1],[2],...' 형태로 요약 인용 목록."
    )
    _ = prompt  # unused when client is stub
    with _llm_sem_thread:
        answer = client.chat([{"role": "user", "content": prompt}])
    if not answer or answer.startswith("Not implemented"):
        # Fallback answer for stub
        answer = "(stub) 컨텍스트 기반 초안 답변. Citations: " + ", ".join(
            [f"[{i+1}]" for i in range(min(len(cits), req.top_k))]
        )
    policy = {"refusal": False, "masked": False, "pii_types": [], "reason": ""}
    if req.enforce_policy:
        pol = enforce_policy(req.query, answer)
        answer = pol["answer"]
        policy = {k: pol[k] for k in ["refusal", "masked", "pii_types", "reason"]}
        if pol["refusal"]:
            # On refusal, strip citations to avoid leaking sensitive refs
            cits = []

    return RagResponse(answer=answer, citations=cits, policy=policy)


from fastapi.responses import StreamingResponse


@app.post("/rag/stream")
async def rag_stream(req: RagRequest):
    mode = req.mode
    if mode == "auto":
        mode = "table" if _detect_table_mode(req.query) else "normal"

    hits = do_hybrid(req.query, top_k=max(10, req.top_k), filters=req.filters or {})
    ctx = "\n\n".join([f"[{i+1}] {h['snippet']}" for i, h in enumerate(hits[: req.top_k])])
    cits = [
        {
            "id": h["id"],
            "title": h.get("title"),
            "source": h.get("source"),
            "post_id": h.get("post_id"),
        }
        for h in hits[: req.top_k]
    ]

    client = LLMClient()
    prompt = (
        "질의에 답하세요. 각 주장 뒤에 반드시 [n] 인용 번호를 붙이세요.\n"
        "인용은 아래 컨텍스트에서만 선택하세요.\n\n"
        f"질의: {req.query}\n\n컨텍스트:\n{ctx}\n\n"
        "출력: 답변 본문과 마지막 줄에 'Citations: [1],[2],...' 형태로 요약 인용 목록."
    )

    async def _gen():
        async with _llm_sem_async:
            yield "event: start\n\n"
            try:
                for delta in client.chat_stream([{ "role": "user", "content": prompt }]):
                    if not delta:
                        continue
                    yield f"data: {delta}\n\n"
            except Exception:
                yield "event: error\n\n"
            finally:
                import json as _json
                yield "event: citations\n"
                yield f"data: {_json.dumps(cits, ensure_ascii=False)}\n\n"
                yield "event: end\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


class FeedbackRequest(BaseModel):
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    policy: Dict[str, Any]
    vote: str  # up|down


@app.post("/feedback")
def feedback(req: FeedbackRequest) -> Dict[str, Any]:
    fbdir = os.getenv("FEEDBACK_DIR", "/data/feedback")
    os.makedirs(fbdir, exist_ok=True)
    item = req.model_dump()
    item["ts"] = datetime.utcnow().isoformat()
    path = os.path.join(fbdir, "feedback.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return {"status": "ok"}
