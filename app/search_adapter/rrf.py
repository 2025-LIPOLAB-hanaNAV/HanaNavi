from typing import Dict, List, Tuple


def rrf(
    bm25: List[Tuple[str, float]],
    vec: List[Tuple[str, float]],
    kRR: int = 60,
) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion for two ranked lists.

    Returns a list of (doc_id, score) sorted by fused score desc.
    """
    scores: Dict[str, float] = {}

    for rank, (doc_id, _score) in enumerate(
        sorted(bm25, key=lambda x: x[1], reverse=True), start=1
    ):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (kRR + rank)

    for rank, (doc_id, _score) in enumerate(
        sorted(vec, key=lambda x: x[1], reverse=True), start=1
    ):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (kRR + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
