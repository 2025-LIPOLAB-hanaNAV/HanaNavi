from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

import os as _os
if _os.getenv("IR_BACKEND", "sqlite").lower() == "opensearch":
    from .opensearch_ir import bm25_search  # type: ignore
else:
    from .sqlite_fts import bm25_search
from .qdrant_vec import vector_search
from .rrf import rrf
from app.models.reranker import rerank


def _recency_boost(date_str: str) -> float:
    try:
        # Accept YYYY-MM-DD or ISO dates
        d = datetime.fromisoformat(date_str.split(" ")[0])
        age_days = (datetime.utcnow() - d).days
        # Small boost for newer docs, decays with age
        return max(0.0, 0.2 - 0.2 * min(365, age_days) / 365.0)
    except Exception:
        return 0.0


def _pass_filters(payload: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    if not filters:
        return True
    cat = filters.get("category")
    ft = filters.get("filetype")
    df = filters.get("date_from")
    dt = filters.get("date_to")
    if cat and str(payload.get("category", "")) != str(cat):
        return False
    if ft and str(payload.get("filetype", "")) != str(ft):
        return False
    date_str = str(payload.get("date", payload.get("posted_at", "")))
    if df and date_str and date_str < str(df):
        return False
    if dt and date_str and date_str > str(dt):
        return False
    return True


def hybrid_search(query: str, top_k: int = 20, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    bm25 = bm25_search(query, top_k=50)
    vec = vector_search(query, top_k=50)

    # Prepare lists for RRF (doc_id, score)
    bm25_pairs = [(doc_id, score) for doc_id, score, _ in bm25]
    vec_pairs = [(doc_id, score) for doc_id, score, _ in vec]
    fused = rrf(bm25_pairs, vec_pairs, kRR=60)

    # Merge payloads by preferring vector payload first (has chunk text)
    payload_map: Dict[str, Dict[str, Any]] = {}
    for doc_id, _s, payload in bm25:
        payload_map.setdefault(doc_id, payload)
    for doc_id, _s, payload in vec:
        payload_map[doc_id] = {**payload_map.get(doc_id, {}), **payload}

    # Apply filters and small recency boost
    rescored = []
    for doc_id, score in fused:
        date_str = str(payload_map.get(doc_id, {}).get("date", ""))
        score += _recency_boost(date_str)
        # Include text for reranker
        text = payload_map.get(doc_id, {}).get("text") or payload_map.get(doc_id, {}).get(
            "snippet", ""
        )
        if not filters or _pass_filters(payload_map.get(doc_id, {}), filters):
            rescored.append((doc_id, score, text))

    reranked = rerank(query, rescored[: max(20, top_k)], top_k=top_k)
    results: List[Dict[str, Any]] = []
    for doc_id, score in reranked:
        payload = payload_map.get(doc_id, {})
        title = payload.get("title") or payload.get("post_id") or doc_id
        text = payload.get("text") or payload.get("snippet") or ""
        source = payload.get("source") or f"{title}#chunk:{payload.get('chunk_id','?')}"
        # Derive post_id from doc_id if not present (e.g., FTS row: post:<rowid>)
        pid = payload.get("post_id")
        if not pid and doc_id.startswith("post:"):
            pid = doc_id.split(":", 1)[1]
        results.append(
            {
                "id": doc_id,
                "score": float(score),
                "snippet": text[:300],
                "source": source,
                "title": title,
                "post_id": pid,
                "filetype": payload.get("filetype"),
                "posted_at": payload.get("date") or payload.get("posted_at"),
                "category": payload.get("category"),
            }
        )
    return results
