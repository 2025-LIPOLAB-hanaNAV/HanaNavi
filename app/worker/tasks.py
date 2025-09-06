from typing import Dict, Any

from .celery_app import app


@app.task(name="app.worker.tasks.ingest_from_webhook")
def ingest_from_webhook(event: Dict[str, Any]) -> Dict[str, Any]:
    """Stub task: enqueue ETL pipeline.

    Steps (later): download → parse → chunk → embed → upsert → FTS5 index
    """
    return {"status": "queued", "event": event}

