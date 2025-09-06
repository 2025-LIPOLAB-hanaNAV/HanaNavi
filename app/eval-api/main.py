from typing import Dict, List, Any
import os
import uuid
import json
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import Response, HTMLResponse
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


def _maybe_call_rag(question: str) -> Dict[str, Any]:
    base = os.getenv("RAG_API_BASE")
    if not base:
        return {"answer": "", "citations": [], "latency_ms": 0}
    try:
        import httpx
        import time
        t0 = time.time()
        r = httpx.post(
            base.rstrip("/") + "/rag/query",
            json={"query": question, "top_k": 8, "enforce_policy": True},
            timeout=60.0,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "answer": data.get("answer", ""),
            "citations": data.get("citations", []),
            "latency_ms": int((time.time() - t0) * 1000),
        }
    except Exception:
        return {"answer": "", "citations": [], "latency_ms": 0}


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
        rag = _maybe_call_rag(s.get("question", "")) if not s.get("candidate_answer") else {"answer": s.get("candidate_answer"), "citations": [], "latency_ms": 0}
        ans = rag.get("answer", "")
        sample = dict(s)
        sample["candidate_answer"] = ans
        j = judge_once(sample)
        results.append({
            "id": s.get("id"),
            **j,
            "rag_latency_ms": rag.get("latency_ms", 0),
            "citation_count": len(rag.get("citations", [])),
        })

    # Aggregate
    def avg(key: str) -> float:
        vals = [float(x.get(key, 0.0)) for x in results]
        return sum(vals) / len(vals) if vals else 0.0

    refusal_rate = sum(1 for x in results if x.get("refusal")) / max(1, len(results))
    pii_rate = sum(1 for x in results if x.get("pii_detected")) / max(1, len(results))
    avg_rag_latency = sum(x.get("rag_latency_ms", 0) for x in results) / max(1, len(results))
    avg_citations = sum(x.get("citation_count", 0) for x in results) / max(1, len(results))
    metrics = {
        "job_id": job_id,
        "dataset": req.dataset,
        "summary": {
            "score_accuracy": round(avg("score_accuracy"), 3),
            "score_relevance": round(avg("score_relevance"), 3),
            "score_readability": round(avg("score_readability"), 3),
            "refusal_rate": round(refusal_rate, 3),
            "pii_detected_rate": round(pii_rate, 3),
            "avg_rag_latency_ms": round(avg_rag_latency, 1),
            "avg_citation_count": round(avg_citations, 2),
        },
        "items": results,
        "created_at": datetime.utcnow().isoformat(),
    }
    # Write JSON and CSV
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    try:
        import csv

        csv_path = path.replace(".json", ".csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as cf:
            writer = csv.writer(cf)
            writer.writerow(["id", "score_accuracy", "score_relevance", "score_readability", "refusal", "pii_detected", "rag_latency_ms", "citation_count"])  # noqa: E501
            for it in results:
                writer.writerow([
                    it.get("id"), it.get("score_accuracy"), it.get("score_relevance"), it.get("score_readability"),
                    it.get("refusal"), it.get("pii_detected"), it.get("rag_latency_ms"), it.get("citation_count"),
                ])
    except Exception:
        pass
    return EvalRunResponse(job_id=job_id, status="completed")


class JudgeEvalRequest(BaseModel):
    question: str
    answer: str
    gold_answer: str | None = None
    policy_rule: str | None = None


@app.post("/judge/eval")
def judge_eval(req: JudgeEvalRequest) -> Dict[str, Any]:
    return judge_once(req.model_dump())


# Simple dashboard and metrics
try:
    from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

    REQ_COUNTER = Counter("eval_requests_total", "Total requests", ["path"])  # type: ignore

    @app.middleware("http")
    async def _metrics_middleware(request, call_next):  # type: ignore
        response = await call_next(request)
        try:
            REQ_COUNTER.labels(path=request.url.path).inc()  # type: ignore
        except Exception:
            pass
        return response

    @app.get("/metrics")
    def metrics():  # type: ignore
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
except Exception:
    pass


@app.get("/reports/list")
def reports_list() -> Dict[str, Any]:
    rd = _reports_dir()
    items = []
    for fn in sorted(os.listdir(rd)) if os.path.exists(rd) else []:
        if not fn.endswith(".json"):
            continue
        items.append({"file": fn})
    return {"reports": items}


@app.get("/reports", response_class=HTMLResponse)
def reports_html():
    rd = _reports_dir()
    rows = []
    for fn in sorted(os.listdir(rd)) if os.path.exists(rd) else []:
        if not fn.endswith(".json"):
            continue
        path = os.path.join(rd, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            s = data.get("summary", {})
            rows.append((fn, s))
        except Exception:
            continue
    html = ["<html><body><h3>Evaluation Reports</h3><table border=1 cellspacing=0 cellpadding=4>"]
    html.append("<tr><th>file</th><th>accuracy</th><th>relevance</th><th>readability</th><th>refusal_rate</th><th>pii_rate</th><th>avg_rag_latency_ms</th><th>avg_citation_count</th></tr>")  # noqa: E501
    for fn, s in rows:
        html.append(
            f"<tr><td>{fn}</td><td>{s.get('score_accuracy',0)}</td><td>{s.get('score_relevance',0)}</td><td>{s.get('score_readability',0)}</td><td>{s.get('refusal_rate',0)}</td><td>{s.get('pii_detected_rate',0)}</td><td>{s.get('avg_rag_latency_ms',0)}</td><td>{s.get('avg_citation_count',0)}</td></tr>"  # noqa: E501
        )
    html.append("</table></body></html>")
    return "\n".join(html)


# Weekly scheduler
import asyncio


@app.on_event("startup")
async def _weekly_scheduler():
    if os.getenv("EVAL_WEEKLY_ENABLED", "0") != "1":
        return
    day = os.getenv("EVAL_WEEKLY_DAY", "sun")  # mon..sun
    at = os.getenv("EVAL_WEEKLY_AT", "03:00")  # HH:MM
    last_flag = os.path.join(_reports_dir(), "last_weekly.txt")

    async def runner():
        while True:
            try:
                now = datetime.utcnow()
                weekday = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
                hhmm = now.strftime("%H:%M")
                stamp = now.strftime("%Y-%m-%d")
                if weekday == day and hhmm == at:
                    prev = ""
                    if os.path.exists(last_flag):
                        with open(last_flag, "r", encoding="utf-8") as f:
                            prev = f.read().strip()
                    if prev != stamp:
                        # Run all three datasets
                        for ds in ["master", "refusal", "pii"]:
                            try:
                                run_eval(EvalRunRequest(dataset=ds))
                            except Exception:
                                pass
                        with open(last_flag, "w", encoding="utf-8") as f:
                            f.write(stamp)
                await asyncio.sleep(60)
            except Exception:
                await asyncio.sleep(60)

    asyncio.create_task(runner())
