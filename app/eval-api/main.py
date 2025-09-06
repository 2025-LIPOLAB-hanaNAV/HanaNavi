from typing import Dict
import uuid

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


@app.post("/eval/run", response_model=EvalRunResponse)
def run_eval(_: EvalRunRequest) -> EvalRunResponse:
    job_id = str(uuid.uuid4())
    # TODO: enqueue batch evaluation and write reports/metrics_*.json|csv
    return EvalRunResponse(job_id=job_id, status="queued")

