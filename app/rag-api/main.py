from typing import List, Dict, Any
import asyncio
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.search_adapter.hybrid import hybrid_search as do_hybrid
from app.models.llm_client import LLMClient
from app.utils.policy import enforce_policy
from app.utils.answer_enhancement import enhance_answer_quality, add_contextual_info
import os
import json
from datetime import datetime


class SearchRequest(BaseModel):
    query: str
    top_k: int = 20
    filters: Dict[str, Any] | None = None


class SearchResult(BaseModel):
    id: str
    score: float
    snippet: str
    source: str  # document name + page/sheet:cell
    post_id: str | None = None


class SearchResponse(BaseModel):
    results: List[SearchResult]


app = FastAPI(title="rag-api", version="0.1.0")

# CORS for Chatbot UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Wildcard works only when credentials are disabled
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
try:
    from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

    REQ_COUNTER = Counter("rag_requests_total", "Total requests", ["path"])  # type: ignore

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

# LLM concurrency limits
import os as _os
_max_sessions = int(_os.getenv("LLM_MAX_SESSIONS", "4"))
_llm_sem_async = asyncio.Semaphore(_max_sessions)
_llm_sem_thread = threading.BoundedSemaphore(_max_sessions)

# Ensure Qdrant collection exists at startup to avoid noisy 404s
try:
    from app.indexer.index_qdrant import ensure_collection as _ensure_qdrant_collection  # type: ignore
except Exception:  # pragma: no cover
    _ensure_qdrant_collection = None  # type: ignore


@app.on_event("startup")
async def _ensure_vec_collection():  # pragma: no cover
    try:
        if _ensure_qdrant_collection is not None:
            _ensure_qdrant_collection("post_chunks", dim=1024)
    except Exception:
        pass


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/search/hybrid", response_model=SearchResponse)
def hybrid_search(req: SearchRequest) -> SearchResponse:
    rows = do_hybrid(req.query, top_k=req.top_k, filters=req.filters or {})
    results = [
        SearchResult(
            id=r["id"],
            score=r["score"],
            snippet=r.get("snippet", ""),
            source=r.get("source", ""),
            post_id=r.get("post_id"),
        )
        for r in rows
    ]
    return SearchResponse(results=results)


class RagRequest(BaseModel):
    query: str
    top_k: int = 8
    mode: str = "auto"  # auto|table|normal
    enforce_policy: bool = True
    filters: Dict[str, Any] | None = None
    history: List[Dict[str, str]] | None = None  # [{role: user|assistant, content: str}]
    model: str | None = None


class RagResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    policy: Dict[str, Any]


def _detect_table_mode(q: str) -> bool:
    ql = q.lower()
    keywords = ["excel", "xlsx", "표", "시트", "셀", "range", "sheet"]
    return any(k in ql for k in keywords)


def _is_smalltalk(q: str) -> bool:
    ql = q.strip().lower()
    if not ql:
        return True
    greetings = [
        "안녕", "안녕하세요", "하이", "hi", "hello", "헬로", "반가워",
        "좋은 아침", "좋은 저녁", "안부", "고마워", "감사", "thank you", "thanks",
    ]
    if any(g in ql for g in greetings):
        # very short greetings / courtesy
        if len(ql) <= 20:
            return True
    # Domain keywords that imply retrieval
    domain = [
        "보이스피싱", "사기", "규정", "정책", "절차", "계좌", "지급정지", "내부",
        "문서", "첨부", "pdf", "xlsx", "docx", "공지", "가이드", "링크",
    ]
    if any(k in ql for k in domain):
        return False
    # Very short generic utterances are smalltalk
    return len(ql) < 12


def _highlight_snippet(snippet: str, query: str) -> str:
    """snippet에서 query와 관련된 키워드들을 하이라이트"""
    if not snippet or not query:
        return snippet
    
    import re
    # 한글, 영문, 숫자로 구성된 키워드 추출
    query_words = re.findall(r'[가-힣a-zA-Z0-9]+', query.lower())
    if not query_words:
        return snippet
    
    highlighted = snippet
    for word in query_words:
        if len(word) < 2:  # 너무 짧은 키워드는 제외
            continue
        # 대소문자 무관하게 매칭하되 원문의 대소문자 보존
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        highlighted = pattern.sub(lambda m: f"**{m.group()}**", highlighted)
    
    return highlighted


def _dedupe_citations(hits, max_citations=5, query=""):
    """중복 제거: post_id + filename 조합으로 고유성 보장, 최대 5개"""
    seen = set()
    unique_cits = []
    for h in hits:
        post_id = h.get("post_id")
        source = h.get("source", "")
        # filename 추출 (source에서 #chunk: 제거)
        filename = source.split("#chunk:")[0] if "#chunk:" in source else source
        key = (post_id, filename)
        if key not in seen:
            seen.add(key)
            snippet = h.get("snippet", "")
            unique_cits.append({
                "id": h["id"],
                "title": h.get("title"),
                "source": source,
                "post_id": post_id,
                "snippet": snippet,
                "highlighted_snippet": _highlight_snippet(snippet, query)  # 하이라이트된 스니펫
            })
            if len(unique_cits) >= max_citations:
                break
    return unique_cits


def _history_text(history: List[Dict[str, str]] | None, max_turns: int = 4) -> str:
    if not history:
        return ""
    h = history[-max_turns:]
    lines = []
    for m in h:
        role = m.get("role", "user")
        prefix = "사용자" if role == "user" else "도우미"
        lines.append(f"{prefix}: {m.get('content','')}")
    return "\n".join(lines)


def _get_query_type_hints(query: str) -> str:
    """질의 타입에 따른 답변 가이드 힌트"""
    q_lower = query.lower()
    
    if any(w in q_lower for w in ["어떻게", "방법", "절차", "과정", "단계"]):
        return "이 질의는 절차나 방법을 묻고 있습니다. 단계별로 명확하게 구분하여 설명하세요."
    elif any(w in q_lower for w in ["무엇", "정의", "의미", "뜻"]):
        return "이 질의는 정의나 개념을 묻고 있습니다. 핵심 정의를 먼저 제시한 후 부연 설명하세요."
    elif any(w in q_lower for w in ["언제", "시간", "날짜", "일정"]):
        return "이 질의는 시간 관련 정보를 묻고 있습니다. 구체적인 날짜나 기간을 명확히 제시하세요."
    elif any(w in q_lower for w in ["누가", "담당", "연락처"]):
        return "이 질의는 담당자나 연락처 정보를 묻고 있습니다. 정확한 담당 부서나 연락 방법을 제시하세요."
    elif any(w in q_lower for w in ["왜", "이유", "원인"]):
        return "이 질의는 이유나 원인을 묻고 있습니다. 배경과 근거를 논리적으로 설명하세요."
    else:
        return "질의에 대해 핵심 내용을 우선 제시하고, 필요시 세부사항을 보완하세요."


@app.post("/rag/query", response_model=RagResponse)
def rag_query(req: RagRequest) -> RagResponse:
    mode = req.mode
    if mode == "auto":
        mode = "table" if _detect_table_mode(req.query) else "normal"
    smalltalk = _is_smalltalk(req.query)
    hits = [] if smalltalk else do_hybrid(req.query, top_k=max(10, req.top_k), filters=req.filters or {}, model=req.model)
    cits = [] if smalltalk else _dedupe_citations(hits, query=req.query)
    ctx = "\n\n".join([f"[{i+1}] {c['snippet']}" for i, c in enumerate(cits)])

    # Compose prompt (LLM stubbed for now)
    client = LLMClient(model=req.model or None)
    convo = []
    hist = _history_text(req.history)
    if hist:
        convo.append({"role": "user", "content": f"이전 대화:\n{hist}"})
        convo.append({"role": "assistant", "content": "확인했습니다."})
    if smalltalk:
        final_user = f"다음 메시지에 자연스럽고 정중하게 한국어로 답변하세요. 출처나 인용은 붙이지 마세요. 띄어쓰기와 맞춤법을 정확하게 작성하세요.\n\n질의: {req.query}"
    else:
        # 질의 타입에 따른 맞춤형 프롬프트
        query_type_hints = _get_query_type_hints(req.query)
        
        final_user = (
            "아래 제공된 컨텍스트 정보를 바탕으로 질의에 정확하고 유용하게 한국어로 답변하세요.\n"
            f"{query_type_hints}\n"
            "답변 작성 규칙:\n"
            "1. 띄어쓰기와 맞춤법을 정확하게 작성하세요\n"
            "2. 각 주요 내용 뒤에 반드시 [1], [2] 형태의 인용 번호를 붙이세요\n"
            "3. 컨텍스트에 없는 내용은 절대 추가하지 마세요\n"
            "4. 정중하고 전문적이면서도 이해하기 쉬운 톤을 유지하세요\n"
            "5. 핵심 내용을 먼저 제시한 후 세부사항을 설명하세요\n"
            "6. 마지막 줄에 'Citations: [1],[2],...' 형태로 사용된 인용 목록을 정리하세요\n\n"
            f"질의: {req.query}\n\n컨텍스트:\n{ctx}"
        )
    convo.append({"role": "user", "content": final_user})
    with _llm_sem_thread:
        answer = client.chat(convo)
    if not answer or answer.startswith("Not implemented"):
        # Fallback answer for stub
        answer = "(stub) 컨텍스트 기반 초안 답변. Citations: " + ", ".join(
            [f"[{i+1}]" for i in range(min(len(cits), req.top_k))]
        )
    
    # 답변 품질 향상 적용 (정책 검사 전)
    if not smalltalk and answer and not answer.startswith("(stub)"):
        try:
            answer, cits = enhance_answer_quality(answer, cits, req.query)
            answer = add_contextual_info(answer, req.query, cits)
        except Exception:
            pass  # 품질 향상 실패시 원본 사용
    
    policy = {"refusal": False, "masked": False, "pii_types": [], "reason": ""}
    if req.enforce_policy:
        pol = enforce_policy(req.query, answer)
        answer = pol["answer"]
        policy = {k: pol[k] for k in ["refusal", "masked", "pii_types", "reason"]}
        if pol["refusal"]:
            # On refusal, strip citations to avoid leaking sensitive refs
            cits = []

    return RagResponse(answer=answer, citations=cits, policy=policy)


from fastapi.responses import StreamingResponse


@app.post("/rag/stream")
async def rag_stream(req: RagRequest):
    mode = req.mode
    if mode == "auto":
        mode = "table" if _detect_table_mode(req.query) else "normal"

    smalltalk = _is_smalltalk(req.query)
    hits = [] if smalltalk else do_hybrid(req.query, top_k=max(10, req.top_k), filters=req.filters or {}, model=req.model)
    cits = [] if smalltalk else _dedupe_citations(hits, query=req.query)
    ctx = "\n\n".join([f"[{i+1}] {c['snippet']}" for i, c in enumerate(cits)])

    client = LLMClient(model=req.model or None)
    convo = []
    hist = _history_text(req.history)
    if hist:
        convo.append({"role": "user", "content": f"이전 대화:\n{hist}"})
        convo.append({"role": "assistant", "content": "확인했습니다."})
    if smalltalk:
        final_user = f"다음 메시지에 자연스럽고 정중하게 한국어로 답변하세요. 출처나 인용은 붙이지 마세요. 띄어쓰기와 맞춤법을 정확하게 작성하세요.\n\n질의: {req.query}"
    else:
        # 질의 타입에 따른 맞춤형 프롬프트
        query_type_hints = _get_query_type_hints(req.query)
        
        final_user = (
            "아래 제공된 컨텍스트 정보를 바탕으로 질의에 정확하고 유용하게 한국어로 답변하세요.\n"
            f"{query_type_hints}\n"
            "답변 작성 규칙:\n"
            "1. 띄어쓰기와 맞춤법을 정확하게 작성하세요\n"
            "2. 각 주요 내용 뒤에 반드시 [1], [2] 형태의 인용 번호를 붙이세요\n"
            "3. 컨텍스트에 없는 내용은 절대 추가하지 마세요\n"
            "4. 정중하고 전문적이면서도 이해하기 쉬운 톤을 유지하세요\n"
            "5. 핵심 내용을 먼저 제시한 후 세부사항을 설명하세요\n"
            "6. 마지막 줄에 'Citations: [1],[2],...' 형태로 사용된 인용 목록을 정리하세요\n\n"
            f"질의: {req.query}\n\n컨텍스트:\n{ctx}"
        )
    convo.append({"role": "user", "content": final_user})

    async def _gen():
        async with _llm_sem_async:
            yield "event: start\n\n"
            try:
                for delta in client.chat_stream(convo):
                    if not delta:
                        continue
                    yield f"data: {delta}\n\n"
            except Exception:
                yield "event: error\n\n"
            finally:
                import json as _json
                if cits:
                    yield "event: citations\n"
                    yield f"data: {_json.dumps(cits, ensure_ascii=False)}\n\n"
                yield "event: end\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


# LLM utility endpoints (Ollama only)
class LLMModelsResponse(BaseModel):
    models: List[str]


@app.get("/llm/models", response_model=LLMModelsResponse)
def list_llm_models() -> LLMModelsResponse:
    api = os.getenv("LLM_API", "ollama").lower()
    if api != "ollama":
        return LLMModelsResponse(models=[])
    base = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
    try:
        import httpx

        r = httpx.get(base + "/api/tags", timeout=15.0)
        r.raise_for_status()
        data = r.json() or {}
        tags = data.get("models", []) or []
        names = []
        for m in tags:
            name = m.get("name") or m.get("model")
            if name:
                names.append(name)
        return LLMModelsResponse(models=names)
    except Exception:
        return LLMModelsResponse(models=[])


class LLMPullRequest(BaseModel):
    model: str


@app.post("/llm/pull")
def pull_llm_model(req: LLMPullRequest) -> Dict[str, Any]:
    api = os.getenv("LLM_API", "ollama").lower()
    if api != "ollama":
        raise HTTPException(status_code=400, detail="Only supported for LLM_API=ollama")
    base = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
    try:
        import httpx

        # Fire-and-forget style pull
        with httpx.stream("POST", base + "/api/pull", json={"name": req.model}, timeout=None) as r:
            if r.status_code >= 400:
                raise HTTPException(status_code=r.status_code, detail="pull failed")
        return {"status": "started", "model": req.model}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FeedbackRequest(BaseModel):
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    policy: Dict[str, Any]
    vote: str  # up|down


@app.post("/feedback")
def feedback(req: FeedbackRequest) -> Dict[str, Any]:
    fbdir = os.getenv("FEEDBACK_DIR", "/data/feedback")
    os.makedirs(fbdir, exist_ok=True)
    item = req.model_dump()
    item["ts"] = datetime.utcnow().isoformat()
    path = os.path.join(fbdir, "feedback.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return {"status": "ok"}
