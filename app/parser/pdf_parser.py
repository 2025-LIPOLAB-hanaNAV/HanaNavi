from typing import List

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore


def parse_pdf(path: str) -> List[str]:
    """Parse a PDF file into page texts."""
    if not PdfReader:  # pragma: no cover
        return []
    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                texts.append("")
        return texts
    except Exception:
        return []
