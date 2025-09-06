from typing import Dict, List, Any
import os
import uuid
import json
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from .judge import judge_once


class EvalRunRequest(BaseModel):
    dataset: str = "master"  # master | refusal | pii


class EvalRunResponse(BaseModel):
    job_id: str
    status: str


app = FastAPI(title="eval-api", version="0.2.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _reports_dir() -> str:
    return os.getenv("REPORTS_DIR", "/data/reports")


def _datasets_root() -> str:
    return os.getenv("DATASETS_DIR", "datasets")


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _maybe_call_rag(question: str) -> str:
    base = os.getenv("RAG_API_BASE")
    if not base:
        return ""
    try:
        import httpx

        r = httpx.post(
            base.rstrip("/") + "/rag/query",
            json={"query": question, "top_k": 8, "enforce_policy": True},
            timeout=60.0,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("answer", "")
    except Exception:
        return ""


@app.post("/eval/run", response_model=EvalRunResponse)
def run_eval(req: EvalRunRequest) -> EvalRunResponse:
    job_id = str(uuid.uuid4())
    os.makedirs(_reports_dir(), exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(_reports_dir(), f"metrics_{req.dataset}_{ts}.json")

    # Load dataset
    if req.dataset == "master":
        dpath = os.path.join(_datasets_root(), "master", "voice_phishing_master_ko.jsonl")
    elif req.dataset == "refusal":
        dpath = os.path.join(_datasets_root(), "refusal", "refusal_ko.jsonl")
    elif req.dataset == "pii":
        dpath = os.path.join(_datasets_root(), "pii", "pii_exposure_ko.jsonl")
    else:
        dpath = os.path.join(_datasets_root(), req.dataset)

    items = _read_jsonl(dpath)

    results: List[Dict[str, Any]] = []
    for s in items:
        ans = s.get("candidate_answer") or _maybe_call_rag(s.get("question", ""))
        sample = dict(s)
        sample["candidate_answer"] = ans
        j = judge_once(sample)
        results.append({"id": s.get("id"), **j})

    # Aggregate
    def avg(key: str) -> float:
        vals = [float(x.get(key, 0.0)) for x in results]
        return sum(vals) / len(vals) if vals else 0.0

    refusal_rate = sum(1 for x in results if x.get("refusal")) / max(1, len(results))
    pii_rate = sum(1 for x in results if x.get("pii_detected")) / max(1, len(results))
    metrics = {
        "job_id": job_id,
        "dataset": req.dataset,
        "summary": {
            "score_accuracy": round(avg("score_accuracy"), 3),
            "score_relevance": round(avg("score_relevance"), 3),
            "score_readability": round(avg("score_readability"), 3),
            "refusal_rate": round(refusal_rate, 3),
            "pii_detected_rate": round(pii_rate, 3),
        },
        "items": results,
        "created_at": datetime.utcnow().isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    return EvalRunResponse(job_id=job_id, status="completed")


class JudgeEvalRequest(BaseModel):
    question: str
    answer: str
    gold_answer: str | None = None
    policy_rule: str | None = None


@app.post("/judge/eval")
def judge_eval(req: JudgeEvalRequest) -> Dict[str, Any]:
    return judge_once(req.model_dump())
