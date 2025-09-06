import os
from typing import List, Tuple, Dict, Any

from app.models.embeddings import embed_query

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Filter
except Exception:  # pragma: no cover
    QdrantClient = None  # type: ignore
    Filter = None  # type: ignore


def _client() -> Any:
    url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    if not QdrantClient:  # pragma: no cover
        raise RuntimeError("qdrant-client not installed")
    return QdrantClient(url=url)


def vector_search(
    query: str,
    collection: str = "post_chunks",
    top_k: int = 50,
) -> List[Tuple[str, float, Dict[str, Any]]]:
    try:
        vec = embed_query([query])[0]
        cli = _client()
        res = cli.search(collection_name=collection, query_vector=vec, limit=top_k)
        out: List[Tuple[str, float, Dict[str, Any]]] = []
        for p in res:
            pid = str(p.id)
            score = float(p.score)
            payload = dict(p.payload or {})
            out.append((pid, score, payload))
        return out
    except Exception:
        # Gracefully degrade if collection is missing or Qdrant not ready
        return []
