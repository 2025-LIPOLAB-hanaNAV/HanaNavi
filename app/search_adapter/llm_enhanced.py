"""
내부 LLM을 활용한 고급 검색 기능
- 쿼리 확장 (동의어, 관련 용어)
- 의도 분석 (질문 유형 분류)
- 컨텍스트 기반 검색 최적화
"""
from typing import List, Dict, Any, Optional
import re

from app.models.llm_client import LLMClient


def _classify_query_intent(query: str) -> Dict[str, Any]:
    """쿼리 의도 분석"""
    q_lower = query.lower()
    
    # 기본 분류
    if any(w in q_lower for w in ["언제", "when", "시간", "날짜", "일정"]):
        return {"type": "temporal", "weight": {"date": 1.5}}
    elif any(w in q_lower for w in ["누가", "who", "담당", "연락처"]):
        return {"type": "person", "weight": {"title": 1.5, "body": 1.3}}
    elif any(w in q_lower for w in ["어디", "where", "위치", "장소"]):
        return {"type": "location", "weight": {"body": 1.5}}
    elif any(w in q_lower for w in ["어떻게", "how", "방법", "절차", "과정"]):
        return {"type": "procedure", "weight": {"body": 2.0, "category": 1.3}}
    elif any(w in q_lower for w in ["무엇", "what", "정의", "의미"]):
        return {"type": "definition", "weight": {"title": 1.8, "body": 1.2}}
    else:
        return {"type": "general", "weight": {"title": 1.2, "body": 1.0}}


def _extract_domain_keywords(query: str) -> List[str]:
    """도메인 특화 키워드 추출"""
    domain_mapping = {
        "보이스피싱": ["전화사기", "스미싱", "피싱", "사기전화", "피해신고"],
        "지급정지": ["계좌정지", "출금정지", "거래정지", "동결", "차단"],
        "내부통제": ["준법감시", "컴플라이언스", "내부감사", "위험관리"],
        "고객": ["손님", "회원", "이용자", "거래자"],
        "시스템": ["전산", "프로그램", "SW", "애플리케이션", "앱"],
        "보안": ["정보보호", "사이버", "해킹", "악성코드", "바이러스"],
        "규정": ["정책", "지침", "절차", "매뉴얼", "가이드라인"],
        "계좌": ["통장", "예금", "적금", "대출"],
    }
    
    expanded = []
    for keyword, synonyms in domain_mapping.items():
        if keyword in query:
            expanded.extend(synonyms)
        for syn in synonyms:
            if syn in query:
                expanded.append(keyword)
                break
    
    return list(set(expanded))


def expand_query_with_llm(query: str, model: Optional[str] = None) -> Dict[str, Any]:
    """LLM을 활용한 쿼리 확장"""
    client = LLMClient(model=model)
    
    # LLM에게 쿼리 분석 요청
    prompt = f"""
다음 검색 쿼리를 분석하여 JSON 형태로 답변해주세요:

질의: {query}

다음 정보를 포함해주세요:
1. keywords: 핵심 키워드 목록 (원본 + 동의어)
2. intent: 질의 의도 (정보검색/절차문의/정의확인/기타)
3. category_hints: 관련 가능한 카테고리 (보이스피싱/내부통제/시스템/기타)
4. expanded_query: 확장된 검색 쿼리

응답은 반드시 JSON 형태로만 답변하세요.
"""
    
    try:
        response = client.chat([{"role": "user", "content": prompt}])
        # JSON 파싱 시도
        if response and response.strip().startswith("{"):
            import json
            result = json.loads(response.strip())
            return result
    except Exception:
        pass
    
    # LLM 실패시 규칙 기반 폴백
    intent_info = _classify_query_intent(query)
    domain_keywords = _extract_domain_keywords(query)
    
    return {
        "keywords": [query] + domain_keywords,
        "intent": intent_info["type"],
        "category_hints": _guess_categories(query),
        "expanded_query": query + " " + " ".join(domain_keywords),
        "field_weights": intent_info["weight"]
    }


def _guess_categories(query: str) -> List[str]:
    """규칙 기반 카테고리 추정"""
    q_lower = query.lower()
    categories = []
    
    if any(w in q_lower for w in ["보이스피싱", "사기", "피싱", "스미싱"]):
        categories.append("보이스피싱")
    if any(w in q_lower for w in ["내부통제", "준법", "컴플라이언스", "감사"]):
        categories.append("내부통제")
    if any(w in q_lower for w in ["시스템", "전산", "프로그램", "SW"]):
        categories.append("시스템")
    if any(w in q_lower for w in ["정책", "규정", "지침", "절차"]):
        categories.append("정책")
    
    return categories


def build_enhanced_opensearch_query(original_query: str, llm_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """LLM 분석 결과를 바탕으로 고급 OpenSearch 쿼리 구성"""
    
    # 기본 멀티매치 쿼리
    must_queries = []
    should_queries = []
    
    # 원본 쿼리
    field_weights = llm_analysis.get("field_weights", {"title": 2.0, "body": 1.0})
    fields = []
    for field, weight in field_weights.items():
        if field == "title":
            fields.append(f"title^{weight}")
        elif field == "body":
            fields.append(f"body^{weight}")
        elif field == "tags":
            fields.append(f"tags^{weight}")
        elif field == "category":
            fields.append(f"category^{weight}")
    
    must_queries.append({
        "multi_match": {
            "query": original_query,
            "fields": fields or ["title^2", "body"],
            "type": "best_fields",
            "operator": "and",
            "fuzziness": "AUTO"
        }
    })
    
    # 확장 키워드로 should 쿼리 추가
    keywords = llm_analysis.get("keywords", [])
    for keyword in keywords[1:]:  # 첫 번째는 원본이므로 제외
        should_queries.append({
            "multi_match": {
                "query": keyword,
                "fields": fields or ["title^1.5", "body"],
                "type": "phrase",
                "boost": 0.7
            }
        })
    
    # 카테고리 힌트 활용
    category_hints = llm_analysis.get("category_hints", [])
    for cat in category_hints:
        should_queries.append({
            "term": {
                "category": {
                    "value": cat,
                    "boost": 1.3
                }
            }
        })
    
    # 최종 쿼리 구성
    query_body = {
        "query": {
            "bool": {
                "must": must_queries,
                "should": should_queries,
                "minimum_should_match": 0 if not should_queries else 1
            }
        },
        "highlight": {
            "fields": {
                "body": {"fragment_size": 150, "number_of_fragments": 2},
                "title": {"fragment_size": 80, "number_of_fragments": 1}
            }
        }
    }
    
    return query_body


def semantic_search_rerank(query: str, candidates: List[Dict[str, Any]], model: Optional[str] = None) -> List[Dict[str, Any]]:
    """LLM을 활용한 의미적 재랭킹"""
    if not candidates or len(candidates) <= 2:
        return candidates
    
    client = LLMClient(model=model)
    
    # 후보 문서들을 텍스트로 변환
    docs_text = []
    for i, doc in enumerate(candidates[:10]):  # 상위 10개만 처리
        title = doc.get("title", "")
        snippet = doc.get("snippet", "")
        text = f"[문서{i+1}] 제목: {title}\n내용: {snippet}"
        docs_text.append(text)
    
    docs_summary = "\n\n".join(docs_text)
    
    prompt = f"""
다음은 "{query}" 질의에 대한 검색 결과들입니다. 
질의와의 관련성을 기준으로 1-10 순서로 재정렬해주세요.

{docs_summary}

응답 형식: 1,3,2,5,4,... (번호만 쉼표로 구분)
"""
    
    try:
        response = client.chat([{"role": "user", "content": prompt}])
        if response:
            # 순서 파싱
            order_str = response.strip()
            if re.match(r'^[\d,\s]+$', order_str):
                order_indices = [int(x.strip()) - 1 for x in order_str.split(",") if x.strip().isdigit()]
                # 유효한 인덱스만 필터링
                valid_indices = [i for i in order_indices if 0 <= i < len(candidates)]
                reranked = [candidates[i] for i in valid_indices]
                # 누락된 문서들을 뒤에 추가
                remaining = [doc for i, doc in enumerate(candidates) if i not in valid_indices]
                return reranked + remaining
    except Exception:
        pass
    
    return candidates