from typing import List


def embed_texts(texts: List[str], dim: int = 1024) -> List[List[float]]:
    """Stub embedding: returns zero vectors with the given dimension.

    Replace with sentence-transformers: dragonkue/snowflake-arctic-embed-l-v2.0-ko.
    """
    return [[0.0] * dim for _ in texts]

