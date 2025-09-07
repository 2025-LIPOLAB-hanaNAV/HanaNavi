import os
from typing import List, Tuple, Dict, Any


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


def bm25_search(query: str, top_k: int = 50) -> List[Tuple[str, float, Dict[str, Any]]]:
    idx = os.getenv("OPENSEARCH_INDEX", "posts")
    cli = _client()
    try:
        body = {
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
                    "body": {"fragment_size": 150, "number_of_fragments": 1},
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
        res = cli.search(index=idx, body=body)
        hits = res.get("hits", {}).get("hits", [])
        out: List[Tuple[str, float, Dict[str, Any]]] = []
        for h in hits:
            _id = h.get("_id") or ""
            score = float(h.get("_score") or 0.0)
            src = h.get("_source", {}) or {}
            hl = h.get("highlight", {}) or {}
            frag = None
            try:
                frag = (hl.get("body") or [None])[0]
            except Exception:
                frag = None
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
            }
            out.append((_id, score, payload))
        return out
    except Exception:
        return []
