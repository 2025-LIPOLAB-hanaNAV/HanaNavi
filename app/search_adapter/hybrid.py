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


def hybrid_search(query: str, top_k: int = 20, filters: Optional[Dict[str, Any]] = None, model: Optional[str] = None) -> List[Dict[str, Any]]:
    # 분리된 검색 전략: OpenSearch(게시글) + Qdrant(첨부파일)
    import os as _os
    ir_backend = _os.getenv("IR_BACKEND", "sqlite").lower()
    
    # IR 백엔드가 disabled인 경우 BM25 검색 건너뛰기
    if ir_backend == "disabled":
        bm25 = []  # 빈 결과로 벡터 검색만 사용
    elif ir_backend == "opensearch":
        bm25 = bm25_search(query, top_k=30, model=model)  # OpenSearch - LLM 향상 적용
    else:
        bm25 = bm25_search(query, top_k=30)  # SQLite - 기본 검색
    vec = vector_search(query, top_k=30)  # 첨부파일 검색

    # 게시글 검색 결과 처리 (OpenSearch/SQLite)
    board_results = []
    for doc_id, score, payload in bm25:
        date_str = str(payload.get("date", ""))
        score += _recency_boost(date_str) + 0.1  # 게시글에 약간 더 높은 가중치
        text = payload.get("snippet", "")
        if not filters or _pass_filters(payload, filters):
            board_results.append((doc_id, score, text, payload, "board"))

    # 첨부파일 검색 결과 처리 (Qdrant)
    attachment_results = []
    for doc_id, score, payload in vec:
        date_str = str(payload.get("date", payload.get("posted_at", "")))
        score += _recency_boost(date_str)
        text = payload.get("text", "")
        if not filters or _pass_filters(payload, filters):
            attachment_results.append((doc_id, score, text, payload, "attachment"))

    # 전체 결과 병합 및 재랭킹
    all_candidates = board_results + attachment_results
    all_candidates.sort(key=lambda x: x[1], reverse=True)
    
    # 상위 후보들에 대해 재랭킹 적용
    rerank_input = [(doc_id, score, text) for doc_id, score, text, _, _ in all_candidates[:max(40, top_k*2)]]
    reranked = rerank(query, rerank_input, top_k=top_k)
    
    # 원본 payload 정보 복원 및 결과 구성
    id_to_payload = {doc_id: (payload, source_type) for doc_id, _, _, payload, source_type in all_candidates}
    
    results: List[Dict[str, Any]] = []
    for doc_id, score in reranked:
        payload, source_type = id_to_payload.get(doc_id, ({}, "unknown"))
        
        if source_type == "board":
            title = payload.get("title", "")
            text = payload.get("snippet", "")
            source = f"{title} (게시글)"
            pid = payload.get("post_id") or (doc_id.split(":", 1)[1] if doc_id.startswith("post:") else None)
        else:  # attachment
            title = payload.get("title", "")
            text = payload.get("text", "")
            source = payload.get("source", f"{title}#chunk:{payload.get('chunk_id','?')}")
            pid = payload.get("post_id")
        
        results.append({
            "id": doc_id,
            "score": float(score),
            "snippet": text[:300],
            "source": source,
            "title": title,
            "post_id": pid,
            "filetype": payload.get("filetype"),
            "posted_at": payload.get("date") or payload.get("posted_at"),
            "category": payload.get("category"),
            "source_type": source_type,  # 구분용 추가 필드
        })
    return results
