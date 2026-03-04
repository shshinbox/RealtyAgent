from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import json
from typing import Optional, Dict


# NodeType 별 사용자 친화적 메시지 매핑
NODE_DISPLAY_NAMES = {
    "initializer": "사용자 쿼리 초기화 중...",
    "planner": "질문 분석 및 계획 수립 중...",
    "dispatcher": "작업 분배 중...",
    "legal_retriever": "관련 법령 검색 중...",
    "doc_retriever": "문서 검색 중...",
    "memory_retriever": "메모리 검색 중...",
    "generator": "답변 생성 중...",
    "verifier": "답변 검증 중...",
    "evaluator": "답변 평가 중...",
    "human_reviewer": "검토 대기 중...",
    "finalizer": "답변 구성이 완료되었습니다.",
}


class HtmlRenderer:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader("server/templates"), autoescape=True
        )

    async def render(self, content: str, title: str = "REPORT") -> str:
        """
        HTML 문자열을 생성해서 반환
        """
        template = self.env.get_template("reports.html")
        html = template.render(
            title=title,
            content=content,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        return html

    async def render_content(self, chunk: str, is_json: bool = False) -> str:
        """
        스트리밍용 HTML 덩어리로 변환
        - chunk 단위로 브라우저 DOM에 적용 가능
        - JSON은 <pre> 태그로 포매팅하고, 일반 텍스트는 <div>로 래핑
        """
        if is_json:
            # JSON은 <pre> 태그로 감싸서 포매팅 (escape 없음)
            template = self.env.from_string(
                """<pre class="ai-json-chunk" data-created="{{ created_at }}">{{ content }}</pre>"""
            )
        else:
            # 일반 텍스트는 escape 처리
            template = self.env.from_string(
                """<div class="ai-chunk" data-created="{{ created_at }}">{{ content | e }}</div>"""
            )

        html_snippet = template.render(
            content=chunk,
            created_at=datetime.now().strftime("%H:%M:%S"),
        )
        return html_snippet

    def format_event(self, event: Dict) -> Optional[tuple[str, bool]]:
        """
        LangGraph 이벤트를 필터링하고 사용자 친화적 메시지로 변환
        - 의미 있는 이벤트만 선택해서 반환
        - raw 디버깅 데이터는 필터링

        Returns:
            (메시지, JSON 여부) 튜플 또는 None (필터링된 경우)
        """
        event_type = event.get("event")

        # on_chain_start: 노드 실행 시작 - 진행 상황 표시
        if event_type == "on_chain_start":
            data = event.get("data", {})
            metadata = event.get("metadata", {})

            # 노드 이름 추출 (name 필드는 NodeType enum이거나 문자열)
            node_name = event.get("name")
            if node_name:
                # NodeType enum일 수 있으므로 문자열로 변환
                node_str = str(node_name).lower()
                # <NodeType.PLANNER: 'planner'> 같은 형식에서 노드 이름 추출
                if ":" in node_str:
                    node_str = node_str.split("'")[1]

                display_name = NODE_DISPLAY_NAMES.get(node_str)
                if display_name:
                    return (display_name, False)

        # on_chain_end: 노드 완료 후 상태 메시지
        elif event_type == "on_chain_end":
            node_name = event.get("name")
            if node_name:
                node_str = str(node_name).lower()
                if ":" in node_str:
                    node_str = node_str.split("'")[1]

                # generator 노드에서 최종 답변을 출력
                if node_str == "generator":
                    data = event.get("data", {})
                    output = data.get("output")

                    if output and isinstance(output, dict):
                        if "answer" in output:
                            answer = output.get("answer")
                            if answer:
                                # JSON인지 확인
                                is_json_response = answer.strip().startswith(
                                    "{"
                                ) and answer.strip().endswith("}")
                                return (
                                    f"📋 최종 답변\n\n{answer}",
                                    is_json_response,
                                )
                
                # evaluator 노드에서 평가 결과 표시
                elif node_str == "evaluator":
                    data = event.get("data", {})
                    output = data.get("output")
                    
                    if output and isinstance(output, dict):
                        evaluation_response = output.get("evaluation_response")
                        retry_count = output.get("retry_count", 0)
                        next_node = output.get("next_node")
                        
                        if evaluation_response:
                            # EvaluationResponse는 Pydantic 객체이므로 속성으로 접근
                            is_safe = getattr(evaluation_response, "is_secured", True)
                            is_grounded = getattr(evaluation_response, "is_grounded", True)
                            
                            if not is_safe:
                                return ("⚠️ 보안 검증 실패: 검토자에게 전달됩니다.", False)
                            elif not is_grounded:
                                if retry_count < 3:
                                    return (f"🔄 재생성 중... (시도 {retry_count + 1}/3)", False)
                                else:
                                    return ("⚠️ 최대 재시도 횟수 초과: 검토자에게 전달됩니다.", False)
                            else:
                                return ("✅ 평가 통과!", False)

        # on_stream: 스트리밍 토큰 (대량의 데이터) - 무시
        # on_tool_start, on_tool_end: 도구 호출 - 무시
        # 나머지 이벤트는 무시

        return None
