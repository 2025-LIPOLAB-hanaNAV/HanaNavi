from typing import Optional, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel


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
    # TODO: enqueue job for worker (download → parse → chunk → index)
    return {"status": "accepted", "event": event.model_dump()}

