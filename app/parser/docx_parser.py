from typing import List

try:
    import docx  # python-docx
except Exception:  # pragma: no cover
    docx = None  # type: ignore


def parse_docx(path: str) -> List[str]:
    """Parse a Word document into paragraphs."""
    if not docx:  # pragma: no cover
        return []
    try:
        d = docx.Document(path)
        paras = [p.text for p in d.paragraphs if p.text]
        return paras
    except Exception:
        return []
