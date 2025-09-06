import os
import hashlib
import json
from typing import List, Callable, Optional


_st_model = None
_redis = None


def _try_load_st() -> Callable[[List[str]], List[List[float]]]:
    global _st_model
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except Exception:  # pragma: no cover
        return lambda texts: [[0.0] * 1024 for _ in texts]

    model_name = os.getenv(
        "EMBEDDING_MODEL", "dragonkue/snowflake-arctic-embed-l-v2.0-ko"
    )
    if _st_model is None:
        _st_model = SentenceTransformer(model_name)

    def _embed(texts: List[str]) -> List[List[float]]:
        vecs = _st_model.encode(texts, batch_size=int(os.getenv("EMBED_BATCH", "32")))
        # L2 normalize
        import numpy as np

        vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
        return vecs.tolist()

    return _embed


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if os.getenv("EMBED_CACHE", "none").lower() != "redis":
        return None
    try:
        import redis  # type: ignore
    except Exception:  # pragma: no cover
        return None
    url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    _redis = redis.from_url(url)
    try:
        _redis.ping()
    except Exception:  # pragma: no cover
        _redis = None
    return _redis


def _prefix(text: str, role: str) -> str:
    use_tpl = os.getenv("EMBED_USE_TEMPLATE", "1") == "1"
    if not use_tpl:
        return text
    if role == "query":
        pref = os.getenv("EMBED_QUERY_PREFIX", "query: ")
    else:
        pref = os.getenv("EMBED_PASSAGE_PREFIX", "passage: ")
    return f"{pref}{text}"


def _hash_key(text: str, role: str, dim: int) -> str:
    h = hashlib.sha1()
    model_name = os.getenv("EMBEDDING_MODEL", "dragonkue/snowflake-arctic-embed-l-v2.0-ko")
    key_src = json.dumps(
        {
            "model": model_name,
            "role": role,
            "dim": dim,
            "use_tpl": os.getenv("EMBED_USE_TEMPLATE", "1"),
            "qpref": os.getenv("EMBED_QUERY_PREFIX", "query: "),
            "ppref": os.getenv("EMBED_PASSAGE_PREFIX", "passage: "),
            "text": text,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    h.update(key_src)
    return h.hexdigest()


def embed_texts(texts: List[str], dim: int = 1024, role: str = "passage") -> List[List[float]]:
    """Embedding helper with optional ST backend and Redis cache.

    - role: "query" or "passage" (applies templates if enabled)
    - Cache: set EMBED_CACHE=redis to reuse vectors across processes
    """
    use_st = os.getenv("USE_ST", "0") == "1"
    red = _get_redis()

    keys = [_hash_key(t, role, dim) for t in texts]
    vecs: List[Optional[List[float]]] = [None] * len(texts)

    # Try cache fetch
    if red is not None:
        try:
            pipe = red.pipeline()
            for k in keys:
                pipe.get(f"embed:{k}")
            cached = pipe.execute()
            for i, raw in enumerate(cached):
                if raw:
                    try:
                        vecs[i] = json.loads(raw)
                    except Exception:
                        vecs[i] = None
        except Exception:
            pass

    # Prepare texts to embed (prefix templates)
    to_embed_idx: List[int] = [i for i, v in enumerate(vecs) if v is None]
    if to_embed_idx:
        prep = [_prefix(texts[i], role) for i in to_embed_idx]
        computed: List[List[float]]
        if use_st:
            embedder = _try_load_st()
            computed = embedder(prep)
        else:
            computed = [[0.0] * dim for _ in prep]
        for idx, v in zip(to_embed_idx, computed):
            vecs[idx] = v
            if red is not None:
                try:
                    red.set(f"embed:{keys[idx]}", json.dumps(v))
                except Exception:
                    pass

    # type: ignore - all filled
    return [v or [0.0] * dim for v in vecs]


def embed_query(texts: List[str], dim: int = 1024) -> List[List[float]]:
    return embed_texts(texts, dim=dim, role="query")


def embed_passages(texts: List[str], dim: int = 1024) -> List[List[float]]:
    return embed_texts(texts, dim=dim, role="passage")
