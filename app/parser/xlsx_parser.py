from typing import List

try:
    import openpyxl
except Exception:  # pragma: no cover
    openpyxl = None  # type: ignore


def parse_xlsx(path: str) -> List[str]:
    """Parse an Excel file into sheet-row texts."""
    if not openpyxl:  # pragma: no cover
        return []
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        out: List[str] = []
        for ws in wb.worksheets:
            rows = []
            for row in ws.iter_rows(values_only=True):
                rows.append("\t".join(["" if v is None else str(v) for v in row]))
            if rows:
                out.append(f"[Sheet:{ws.title}]\n" + "\n".join(rows))
        return out
    except Exception:
        return []
