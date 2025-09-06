import re
from typing import List, Dict, Any, Tuple


PII_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"\b0\d{1,2}-\d{3,4}-\d{4}\b")),
    ("rrn", re.compile(r"\b\d{6}-\d{7}\b")),  # 주민등록번호
    ("credit_card", re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{4}\b")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("account_hint", re.compile(r"(계좌|account)[^0-9]{0,10}([0-9-]{8,})", re.IGNORECASE)),
]


SENSITIVE_KEYWORDS = [
    "주민등록", "주민번호", "사번", "계좌", "카드번호", "전화번호", "휴대전화",
    "email", "이메일", "주소", "개인정보", "PII", "신용카드",
]

INTERNAL_KEYWORDS = [
    "내부용", "비공개", "기밀", "confidential", "internal only", "사내 전용",
]


def detect_pii(text: str) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for name, pat in PII_PATTERNS:
        for m in pat.finditer(text):
            value = m.group(0)
            matches.append({"type": name, "value": value, "span": [m.start(), m.end()]})
    return matches


def mask_pii(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    detections = detect_pii(text)
    masked = text
    # Replace from right to left to preserve indices
    for d in sorted(detections, key=lambda x: x["span"][0], reverse=True):
        start, end = d["span"]
        token = f"[MASKED:{d['type']}]"
        masked = masked[:start] + token + masked[end:]
    return masked, detections


def query_seeks_pii(query: str) -> bool:
    q = query.lower()
    intent_words = ["알려줘", "공개", "보여줘", "list", "extract", "누구", "연락처"]
    if any(k in q for k in [kw.lower() for kw in SENSITIVE_KEYWORDS]):
        if any(w in q for w in intent_words):
            return True
    return False


def detect_internal(text: str) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in INTERNAL_KEYWORDS)


def enforce_policy(query: str, answer: str) -> Dict[str, Any]:
    # Rule 1: If query explicitly seeks PII/internal, refuse
    if query_seeks_pii(query):
        return {
            "refusal": True,
            "masked": False,
            "pii_types": [],
            "reason": "요청이 개인정보/내부정보 제공을 명시적으로 요구합니다.",
            "answer": "정책상 개인정보/내부정보는 제공할 수 없습니다.",
        }

    # Rule 2: Mask any PII detected in answer
    masked, dets = mask_pii(answer)
    pii_types = sorted({d["type"] for d in dets})

    # Rule 3: If answer contains internal keywords, add warning footer
    warning = ""
    if detect_internal(answer):
        warning = "\n\n[주의] 내부 문구가 포함되어 마스킹/축약되었습니다."

    final = masked + warning if warning else masked
    return {
        "refusal": False,
        "masked": masked != answer,
        "pii_types": pii_types,
        "reason": "",
        "answer": final,
    }

