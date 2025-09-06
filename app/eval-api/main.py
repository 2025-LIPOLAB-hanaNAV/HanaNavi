from typing import Dict
import os
import uuid
import json
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel


class EvalRunRequest(BaseModel):
    dataset: str = "master"  # master | refusal | pii


class EvalRunResponse(BaseModel):
    job_id: str
    status: str


app = FastAPI(title="eval-api", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _reports_dir() -> str:
    return os.getenv("REPORTS_DIR", "/data/reports")


@app.post("/eval/run", response_model=EvalRunResponse)
def run_eval(req: EvalRunRequest) -> EvalRunResponse:
    job_id = str(uuid.uuid4())
    # Minimal placeholder: write a dummy metrics file
    os.makedirs(_reports_dir(), exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(_reports_dir(), f"metrics_{req.dataset}_{ts}.json")
    metrics = {
        "job_id": job_id,
        "dataset": req.dataset,
        "summary": {
            "score_accuracy": 0.0,
            "score_relevance": 0.0,
            "score_readability": 0.0,
            "refusal_rate": 0.0,
            "pii_detected_rate": 0.0,
        },
        "items": [],
        "created_at": datetime.utcnow().isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    return EvalRunResponse(job_id=job_id, status="queued")
