from typing import Optional, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel

try:
    # Celery is optional in local dev without worker
    from app.worker.tasks import ingest_from_webhook  # type: ignore
except Exception:  # pragma: no cover
    ingest_from_webhook = None  # type: ignore


class WebhookEvent(BaseModel):
    action: str
    post_id: Optional[int] = None
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


app = FastAPI(title="etl-api", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(event: WebhookEvent) -> Dict[str, Any]:
    payload = event.model_dump()
    task_id = None
    if ingest_from_webhook:
        async_result = ingest_from_webhook.delay(payload)  # type: ignore
        task_id = async_result.id
    return {"status": "accepted", "task_id": task_id, "event": payload}


@app.post("/ingest/webhook")
async def ingest_webhook(event: WebhookEvent) -> Dict[str, Any]:
    """Alias endpoint per WBS spec."""
    return await webhook(event)
