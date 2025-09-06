from typing import List

from fastapi import FastAPI
from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 20


class SearchResult(BaseModel):
    id: str
    score: float
    snippet: str
    source: str  # document name + page/sheet:cell


class SearchResponse(BaseModel):
    results: List[SearchResult]


app = FastAPI(title="rag-api", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/search/hybrid", response_model=SearchResponse)
def hybrid_search(req: SearchRequest) -> SearchResponse:
    # TODO: BM25 top-50 + Vec top-50 → RRF → rerank
    dummy = [
        SearchResult(
            id="doc:example",
            score=1.0,
            snippet="This is a stub result. Replace with real search.",
            source="example.pdf:1",
        )
    ]
    return SearchResponse(results=dummy)

