from typing import List, Dict, Any
import os

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        Distance,
        VectorParams,
        PointStruct,
    )
except Exception:  # pragma: no cover
    QdrantClient = None  # type: ignore
    Distance = None  # type: ignore
    VectorParams = None  # type: ignore
    PointStruct = None  # type: ignore
    # Deletion filter models (optional)
    try:
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue  # type: ignore
    except Exception:
        Filter = FieldCondition = MatchValue = None  # type: ignore


def _client() -> Any:
    url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    if not QdrantClient:  # pragma: no cover
        raise RuntimeError("qdrant-client not installed in this environment")
    return QdrantClient(url=url)


def ensure_collection(name: str, dim: int = 1024) -> None:
    client = _client()
    try:
        client.get_collection(name)
    except Exception:
        client.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def upsert_embeddings(collection: str, points: List[Dict[str, Any]], dim: int = 1024) -> None:
    """Upsert embedding points into Qdrant."""
    if not points:
        return
    ensure_collection(collection, dim)
    client = _client()
    qpoints = [
        PointStruct(
            id=p.get("id"),
            vector=p["vector"],
            payload={k: v for k, v in p.items() if k not in {"id", "vector"}},
        )
        for p in points
    ]
    client.upsert(collection_name=collection, points=qpoints)


def delete_by_post_id(collection: str, post_id: str) -> None:
    client = _client()
    try:
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue  # type: ignore
        flt = Filter(must=[FieldCondition(key="post_id", match=MatchValue(value=post_id))])
        client.delete(collection_name=collection, points_selector=flt)
    except Exception:
        # best-effort; if filter API unavailable, attempt id range fallback
        # Note: our IDs are formatted as f"{post_id}_<chunk>"; we cannot enumerate without metadata
        pass
