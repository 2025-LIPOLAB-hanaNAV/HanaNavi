import os
from typing import List, Tuple, Dict, Any

from .llm_enhanced import expand_query_with_llm, build_enhanced_opensearch_query, semantic_search_rerank


def _client():
    try:
        from opensearchpy import OpenSearch  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("opensearch-py not installed") from e
    url = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
    user = os.getenv("OPENSEARCH_USER")
    password = os.getenv("OPENSEARCH_PASSWORD")
    http_auth = (user, password) if user and password else None
    # Simple URL host string works in opensearch-py
    return OpenSearch(hosts=[url], http_auth=http_auth, verify_certs=False, ssl_show_warn=False)


def bm25_search(query: str, top_k: int = 50, model: str = None, use_llm_enhancement: bool = True) -> List[Tuple[str, float, Dict[str, Any]]]:
    idx = os.getenv("OPENSEARCH_INDEX", "posts")
    cli = _client()
    
    try:
        # LLM 기반 쿼리 향상 (선택적)
        if use_llm_enhancement and os.getenv("LLM_ENHANCED_SEARCH", "1") == "1":
            try:
                llm_analysis = expand_query_with_llm(query, model)
                body = build_enhanced_opensearch_query(query, llm_analysis)
                body["size"] = min(top_k * 2, 100)  # 더 많은 후보 확보
            except Exception:
                # LLM 실패시 기본 쿼리로 폴백
                body = _build_basic_query(query, top_k)
        else:
            body = _build_basic_query(query, top_k)
        
        res = cli.search(index=idx, body=body)
        hits = res.get("hits", {}).get("hits", [])
        
        out: List[Tuple[str, float, Dict[str, Any]]] = []
        for h in hits:
            _id = h.get("_id") or ""
            score = float(h.get("_score") or 0.0)
            src = h.get("_source", {}) or {}
            hl = h.get("highlight", {}) or {}
            
            # 하이라이트된 내용 우선 사용
            frag = None
            try:
                body_frags = hl.get("body", [])
                title_frags = hl.get("title", [])
                if body_frags:
                    frag = " ".join(body_frags[:2])  # 최대 2개 프래그먼트
                elif title_frags:
                    frag = title_frags[0]
            except Exception:
                pass
            
            body_text = src.get("body", "") or ""
            snippet = frag or (body_text[:300] if isinstance(body_text, str) else "")
            
            payload = {
                "title": src.get("title"),
                "snippet": snippet,
                "tags": ",".join(src.get("tags", []) or src.get("tags", "") or []
                                    if isinstance(src.get("tags"), list) else [src.get("tags", "")])
                if src.get("tags") is not None else "",
                "category": src.get("category"),
                "filetype": src.get("filetype"),
                "date": src.get("posted_at"),
                "post_id": _id.replace("post:", "") if _id.startswith("post:") else _id,
            }
            out.append((_id, score, payload))
        
        # LLM 기반 의미적 재랭킹 (선택적)
        if use_llm_enhancement and out and os.getenv("LLM_RERANK", "0") == "1":
            try:
                # 재랭킹을 위해 딕셔너리 형태로 변환
                candidates = []
                for _id, score, payload in out:
                    candidates.append({
                        "id": _id,
                        "score": score,
                        "title": payload.get("title", ""),
                        "snippet": payload.get("snippet", ""),
                        **payload
                    })
                reranked_candidates = semantic_search_rerank(query, candidates, model)
                # 다시 원래 형태로 변환
                out = [(c["id"], c["score"], {k: v for k, v in c.items() if k not in ["id", "score"]}) 
                       for c in reranked_candidates[:top_k]]
            except Exception:
                pass  # 재랭킹 실패시 원본 결과 사용
                
        return out[:top_k]
    except Exception:
        return []


def _build_basic_query(query: str, top_k: int) -> Dict[str, Any]:
    """기본 OpenSearch 쿼리 구성"""
    return {
        "size": top_k,
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "title^2",
                                "body",
                                "tags^1.5",
                                "category",
                            ],
                            "type": "most_fields",
                            "operator": "and",
                            "fuzziness": "AUTO",
                        }
                    },
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^2", "body"],
                            "type": "phrase_prefix",
                        }
                    },
                ]
            }
        },
        "highlight": {
            "fields": {
                "body": {"fragment_size": 150, "number_of_fragments": 2},
                "title": {"fragment_size": 80, "number_of_fragments": 1},
            }
        },
        "_source": [
            "title",
            "body",
            "tags",
            "category",
            "filetype",
            "posted_at",
        ],
    }
