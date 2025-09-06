from typing import Dict, Any

from .celery_app import app
from .pipeline import run_ingest


@app.task(name="app.worker.tasks.ingest_from_webhook")
def ingest_from_webhook(event: Dict[str, Any]) -> Dict[str, Any]:
    """Execute ETL pipeline for the given webhook event."""
    try:
        result = run_ingest(event)
        return {"status": "done", **result}
    except Exception as e:  # pragma: no cover
        return {"status": "error", "message": str(e)}
