import os
from typing import Any, List, Tuple


_ort_session = None
_ce_model = None
_tokenizer = None


def _use_rerank() -> bool:
    return os.getenv("USE_RERANK", "1") == "1"


def _backend() -> str:
    return os.getenv("RERANK_BACKEND", "st")  # st | onnx


def _onnx_session() -> Any:
    global _ort_session
    if _ort_session is not None:
        return _ort_session
    try:
        import onnxruntime as ort
    except Exception:  # pragma: no cover
        return None
    model_path = os.getenv("RERANKER_ONNX_PATH")
    if not model_path or not os.path.exists(model_path):
        return None
    providers = ["CPUExecutionProvider"]
    _ort_session = ort.InferenceSession(model_path, providers=providers)
    return _ort_session


def _onnx_tokenizer():
    global _tokenizer
    if _tokenizer is not None:
        return _tokenizer
    try:
        from transformers import AutoTokenizer
    except Exception:  # pragma: no cover
        return None
    tok_name = os.getenv("RERANKER_TOKENIZER", "BAAI/bge-reranker-small")
    _tokenizer = AutoTokenizer.from_pretrained(tok_name)
    return _tokenizer


def _st_cross_encoder():
    global _ce_model
    if _ce_model is not None:
        return _ce_model
    try:
        from sentence_transformers import CrossEncoder
    except Exception:  # pragma: no cover
        return None
    model_name = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-small")
    _ce_model = CrossEncoder(model_name)
    return _ce_model


def _minmax(xs: List[float]) -> List[float]:
    if not xs:
        return xs
    lo, hi = min(xs), max(xs)
    if hi - lo < 1e-12:
        return [0.5 for _ in xs]
    return [(x - lo) / (hi - lo) for x in xs]


def rerank(
    query: str, items: List[Tuple[str, float, str]], top_k: int = 20
) -> List[Tuple[str, float]]:
    """Rerank candidates using bge-reranker-small.

    items: list of (doc_id, fused_score, text)
    Returns: list of (doc_id, final_score) sorted desc.
    """
    if not _use_rerank() or not items:
        return sorted([(i[0], i[1]) for i in items], key=lambda x: x[1], reverse=True)[
            :top_k
        ]

    backend = _backend()
    texts = [t for _id, _s, t in items]
    fused = [s for _id, s, _t in items]

    ce_scores: List[float] = []
    try:
        if backend == "onnx":
            sess = _onnx_session()
            tok = _onnx_tokenizer()
            if sess is not None and tok is not None:
                pairs = list(zip([query] * len(texts), texts))
                enc = tok(
                    pairs,
                    padding=True,
                    truncation=True,
                    max_length=int(os.getenv("RERANK_MAX_LENGTH", "512")),
                    return_tensors="np",
                )
                feed = {}
                for inp in sess.get_inputs():
                    name = inp.name
                    if name in enc:
                        feed[name] = enc[name]
                out = sess.run(None, feed)
                logits = out[0]
                # Support shapes (batch, 1) or (batch,) or (batch, 2)
                import numpy as np

                arr = np.array(logits)
                if arr.ndim == 2 and arr.shape[1] == 1:
                    ce_scores = arr[:, 0].tolist()
                elif arr.ndim == 2 and arr.shape[1] == 2:
                    ce_scores = arr[:, 1].tolist()
                else:
                    ce_scores = arr.reshape(-1).tolist()
        if not ce_scores:
            # Fallback to Sentence-Transformers CrossEncoder
            ce = _st_cross_encoder()
            if ce is not None:
                pairs = [(query, t) for t in texts]
                preds = ce.predict(pairs)
                ce_scores = [float(x) for x in preds]
    except Exception:
        ce_scores = []

    if not ce_scores:
        # Last resort: no reranker available
        return sorted([(i[0], i[1]) for i in items], key=lambda x: x[1], reverse=True)[
            :top_k
        ]

    # Combine normalized fused score with CE score
    nfused = _minmax(fused)
    nce = _minmax(ce_scores)
    alpha = float(os.getenv("RERANK_ALPHA", "0.7"))
    combined = [alpha * s_ce + (1 - alpha) * s_f for s_ce, s_f in zip(nce, nfused)]
    arr = list(zip([i[0] for i in items], combined))
    return sorted(arr, key=lambda x: x[1], reverse=True)[:top_k]
