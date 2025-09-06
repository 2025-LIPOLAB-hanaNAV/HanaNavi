import os
from typing import List, Callable


_st_model = None


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
        vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
        return vecs.tolist()

    return _embed


def embed_texts(texts: List[str], dim: int = 1024) -> List[List[float]]:
    """Embedding helper with optional Sentence-Transformers backend.

    - If sentence-transformers is available, uses the configured model and L2 normalizes.
    - Otherwise, returns zero vectors with the given dimension (stub).
    """
    use_st = os.getenv("USE_ST", "0") == "1"
    if use_st:
        embedder = _try_load_st()
        return embedder(texts)
    return [[0.0] * dim for _ in texts]
