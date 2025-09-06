from typing import Iterable, List


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    if chunk_size <= 0:
        return [text]
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def chunk_texts(texts: Iterable[str], chunk_size: int = 400, overlap: int = 50) -> List[str]:
    out: List[str] = []
    for t in texts:
        if not t:
            continue
        out.extend(chunk_text(t, chunk_size=chunk_size, overlap=overlap))
    return out

