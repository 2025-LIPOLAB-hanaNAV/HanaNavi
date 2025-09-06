from typing import List, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.search_adapter.hybrid import hybrid_search as do_hybrid
from app.models.llm_client import LLMClient
from app.utils.policy import enforce_policy


class SearchRequest(BaseModel):
    query: str
    top_k: int = 20


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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/search/hybrid", response_model=SearchResponse)
def hybrid_search(req: SearchRequest) -> SearchResponse:
    rows = do_hybrid(req.query, top_k=req.top_k)
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

    hits = do_hybrid(req.query, top_k=max(10, req.top_k))
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
