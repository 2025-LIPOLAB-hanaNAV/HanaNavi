"""
챗봇 답변 품질 향상 유틸리티
- 답변 후처리 및 검증
- 인용 번호 일관성 검사
- 답변 구조화 개선
"""
import re
from typing import List, Dict, Any, Tuple


def validate_and_fix_citations(answer: str, citations: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """답변의 인용 번호와 실제 citations 일관성 검사 및 수정"""
    if not citations:
        # 인용이 없으면 답변에서 인용 번호 제거
        cleaned_answer = re.sub(r'\[(\d+)\]', '', answer)
        cleaned_answer = re.sub(r'Citations?:\s*.*$', '', cleaned_answer, flags=re.MULTILINE | re.IGNORECASE)
        return cleaned_answer.strip(), []
    
    # 답변에서 사용된 인용 번호 추출
    cited_numbers = set()
    for match in re.finditer(r'\[(\d+)\]', answer):
        num = int(match.group(1))
        cited_numbers.add(num)
    
    # 실제 사용된 인용만 필터링
    used_citations = []
    for i, citation in enumerate(citations):
        if (i + 1) in cited_numbers:
            used_citations.append(citation)
    
    # Citations 줄 정리
    citations_pattern = r'Citations?:\s*\[([^\]]+)\].*$'
    if used_citations:
        citation_nums = [str(i + 1) for i in range(len(used_citations))]
        new_citations_line = f"Citations: [{','.join(citation_nums)}]"
        answer = re.sub(citations_pattern, new_citations_line, answer, flags=re.MULTILINE | re.IGNORECASE)
        
        # Citations 줄이 없으면 추가
        if not re.search(citations_pattern, answer, re.MULTILINE | re.IGNORECASE):
            answer = answer.strip() + f"\n\n{new_citations_line}"
    else:
        # 사용된 인용이 없으면 Citations 줄 제거
        answer = re.sub(citations_pattern, '', answer, flags=re.MULTILINE | re.IGNORECASE)
    
    return answer.strip(), used_citations


def improve_korean_formatting(text: str) -> str:
    """한국어 텍스트 포맷팅 개선"""
    if not text:
        return text
    
    # 기본 띄어쓰기 규칙 적용
    # 조사 앞 띄어쓰기 제거 (예: "문서 는" -> "문서는")
    text = re.sub(r'\s+(은|는|이|가|을|를|의|에|에서|로|으로|와|과|도|만|까지|부터|마다)', r'\1', text)
    
    # 숫자와 단위 사이 띄어쓰기 (예: "5개" 유지, "5 개" -> "5개")
    text = re.sub(r'(\d)\s+(개|명|건|번|회|일|년|월|주|시간|분|초|원|달러)', r'\1\2', text)
    
    # 중복 공백 제거
    text = re.sub(r'\s+', ' ', text)
    
    # 문장 부호 앞뒤 공백 정리
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)  # 부호 앞 공백 제거
    text = re.sub(r'([,.!?;:])\s*', r'\1 ', text)  # 부호 뒤 적절한 공백
    
    # 괄호 처리
    text = re.sub(r'\s*\(\s*', ' (', text)  # 여는 괄호 앞 공백
    text = re.sub(r'\s*\)\s*', ') ', text)   # 닫는 괄호 뒤 공백
    
    return text.strip()


def structure_answer(answer: str) -> str:
    """답변 구조 개선"""
    if not answer:
        return answer
    
    lines = answer.split('\n')
    structured_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 주요 포인트를 불릿으로 구조화 (선택적)
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            structured_lines.append(f"• {line[1:].strip()}")
        elif re.match(r'^\d+\.', line):
            # 숫자로 시작하는 목록 유지
            structured_lines.append(line)
        else:
            structured_lines.append(line)
    
    return '\n'.join(structured_lines)


def enhance_answer_quality(answer: str, citations: List[Dict[str, Any]], query: str) -> Tuple[str, List[Dict[str, Any]]]:
    """종합적인 답변 품질 향상"""
    if not answer:
        return answer, citations
    
    # 1. 인용 일관성 검사 및 수정
    answer, filtered_citations = validate_and_fix_citations(answer, citations)
    
    # 2. 한국어 포맷팅 개선
    answer = improve_korean_formatting(answer)
    
    # 3. 답변 구조화
    answer = structure_answer(answer)
    
    # 4. 질의 타입별 후처리
    answer = _post_process_by_query_type(answer, query)
    
    return answer, filtered_citations


def _post_process_by_query_type(answer: str, query: str) -> str:
    """질의 타입별 답변 후처리"""
    query_lower = query.lower()
    
    # 절차/방법 문의인 경우 단계별 구조화
    if any(word in query_lower for word in ["어떻게", "방법", "절차", "과정", "단계"]):
        # 이미 번호가 있는 경우는 유지, 없으면 단계별로 구조화 시도
        if not re.search(r'^\d+\.', answer, re.MULTILINE):
            # 간단한 단계별 구조화 (예: "먼저", "그리고", "마지막으로" 등을 찾아서 번호 매기기)
            step_markers = ["먼저", "그리고", "그 다음", "다음으로", "마지막으로", "최종적으로"]
            for i, marker in enumerate(step_markers):
                if marker in answer:
                    answer = answer.replace(marker, f"{i+1}. {marker}")
    
    # 정의 문의인 경우 명확한 정의 제시
    elif any(word in query_lower for word in ["무엇", "정의", "의미", "뜻"]):
        if not answer.startswith(("이것은", "이는", "그것은")):
            # 정의형 답변으로 시작하도록 유도 (이미 잘 구성된 경우는 건드리지 않음)
            pass
    
    return answer


def add_contextual_info(answer: str, query: str, citations: List[Dict[str, Any]]) -> str:
    """맥락 정보 추가 (필요시)"""
    if not citations:
        return answer
    
    # 출처 다양성 정보 추가
    source_types = set()
    categories = set()
    for cit in citations:
        if cit.get("source_type") == "board":
            source_types.add("게시판")
        elif cit.get("source_type") == "attachment":
            source_types.add("첨부파일")
        if cit.get("category"):
            categories.add(cit.get("category"))
    
    # 맥락 정보가 유용한 경우에만 추가
    if len(source_types) > 1 or len(categories) > 1:
        context_info = []
        if len(source_types) > 1:
            context_info.append(f"출처: {', '.join(source_types)}")
        if len(categories) > 1:
            context_info.append(f"관련 분야: {', '.join(categories)}")
        
        if context_info and len(answer) < 1000:  # 너무 긴 답변에는 추가하지 않음
            context_line = f"\n\n*({', '.join(context_info)}에서 참조)*"
            # Citations 줄 앞에 삽입
            citations_match = re.search(r'\n\nCitations?:\s*.*$', answer, re.IGNORECASE)
            if citations_match:
                answer = answer[:citations_match.start()] + context_line + answer[citations_match.start():]
            else:
                answer += context_line
    
    return answer