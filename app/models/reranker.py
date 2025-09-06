from typing import List, Tuple


def rerank(pairs: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    """Placeholder reranker: sorts by the given score descending."""
    return sorted(pairs, key=lambda x: x[1], reverse=True)

