from typing import Dict, Any
import os


def _client():
    try:
        from opensearchpy import OpenSearch  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("opensearch-py not installed") from e
    url = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
    user = os.getenv("OPENSEARCH_USER")
    password = os.getenv("OPENSEARCH_PASSWORD")
    http_auth = (user, password) if user and password else None
    return OpenSearch(hosts=[url], http_auth=http_auth, verify_certs=False, ssl_show_warn=False)


def ensure_index(index: str = "posts") -> None:
    cli = _client()
    try:
        if cli.indices.exists(index=index):  # type: ignore
            return
    except Exception:
        pass
    body = {
        "settings": {
            "index": {"number_of_shards": 1, "number_of_replicas": 0},
            "analysis": {
                "analyzer": {
                    "ko_analyzer": {
                        "type": "custom",
                        "tokenizer": "nori_tokenizer",
                        "filter": ["lowercase", "nori_part_of_speech"],
                    }
                }
            },
        },
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "ko_analyzer", "search_analyzer": "ko_analyzer"},
                "body": {"type": "text", "analyzer": "ko_analyzer", "search_analyzer": "ko_analyzer"},
                "tags": {"type": "keyword"},
                "category": {"type": "keyword"},
                "filetype": {"type": "keyword"},
                "posted_at": {"type": "keyword"},
                "severity": {"type": "keyword"},
            }
        },
    }
    try:
        cli.indices.create(index=index, body=body)  # type: ignore
    except Exception:
        pass


def upsert_post(post_id: str, title: str, body: str, tags: str, category: str, filetype: str, posted_at: str, severity: str, index: str = "posts") -> None:
    ensure_index(index)
    cli = _client()
    doc = {
        "title": title,
        "body": body,
        "tags": tags.split(",") if tags else [],
        "category": category,
        "filetype": filetype,
        "posted_at": posted_at,
        "severity": severity,
    }
    try:
        cli.index(index=index, id=f"post:{post_id}", body=doc)  # type: ignore
    except Exception:
        pass
