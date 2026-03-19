import json
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from typing import Dict


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
        template = self.env.get_template("reports.html")
        return template.render(
            title=title,
            content=content,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    async def render_content(self, chunk: str, is_json: bool = False) -> str:
        """
        스트리밍용 HTML 덩어리로 변환.
        chunk 앞에 붙는 마커로 렌더링 방식을 결정한다.

        마커 종류:
          __pause__      → data-event="pause" 상태 뱃지 (human_reviewer 대기)
          __report__:    → ai-report-chunk (오른쪽 보고서 패널)
          __counselor__: → ai-counselor-chunk (왼쪽 AI 말풍선)
          그 외           → ai-chunk (왼쪽 상태 뱃지)
        """
        if chunk == "__pause__":
            return '<div class="ai-chunk" data-event="pause">검토 대기 중...</div>'

        if chunk.startswith("__report__:"):
            content = chunk[len("__report__:"):]
            inner = self._render_report_inner(content)
            return f'<div class="ai-report-chunk">{inner}</div>'

        if chunk.startswith("__counselor__:"):
            content = chunk[len("__counselor__:"):]
            template = self.env.from_string(
                """<div class="ai-counselor-chunk" data-created="{{ created_at }}">{{ content | e }}</div>"""
            )
            return template.render(content=content, created_at=datetime.now().strftime("%H:%M:%S"))

        # 일반 상태 뱃지
        template = self.env.from_string(
            """<div class="ai-chunk" data-created="{{ created_at }}">{{ content | e }}</div>"""
        )
        return template.render(content=chunk, created_at=datetime.now().strftime("%H:%M:%S"))

    def _is_report_json(self, text: str) -> bool:
        """answer가 구조화된 보고서 JSON인지 확인."""
        try:
            data = json.loads(text)
            return isinstance(data, dict) and "report_meta" in data
        except (json.JSONDecodeError, Exception):
            return False

    def _render_report_inner(self, content: str) -> str:
        """report 패널 내부 HTML 반환 (ai-report-chunk 래퍼 제외). SSE·history 공용."""
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            data = json.loads(content)
            if "report_meta" in data:
                inner = self.env.get_template("legal_report_panel.html").render(
                    **data, created_at=created_at
                )
                return inner.replace("\n", "").replace("\r", "")
        except (json.JSONDecodeError, Exception):
            pass
        # fallback: plain text (Jinja2 escape)
        return self.env.from_string(
            '<div class="lr-plain">{{ content | e }}</div>'
        ).render(content=content)

    def render_report_html(self, answer: str) -> str:
        """history 로딩용: answer 문자열 → 패널 내부 HTML."""
        return self._render_report_inner(answer)

    def format_event(self, event: Dict) -> list[tuple[str, bool]]:
        """
        LangGraph 이벤트를 필터링하고 렌더링 가능한 청크 목록으로 변환.

        Returns:
            list of (메시지, is_json) 튜플. 빈 리스트 = 무시할 이벤트.
            generator 노드는 chat_message + answer 두 개를 동시에 반환한다.
        """
        event_type = event.get("event")

        # on_chain_start: 노드 실행 시작 → 상태 뱃지
        if event_type == "on_chain_start":
            node_name = event.get("name")
            if node_name:
                node_str = str(node_name).lower()
                if ":" in node_str:
                    node_str = node_str.split("'")[1]

                if node_str == "human_reviewer":
                    return [("__pause__", False)]

                display_name = NODE_DISPLAY_NAMES.get(node_str)
                if display_name:
                    return [(display_name, False)]

        # on_chain_end: 노드 완료
        elif event_type == "on_chain_end":
            node_name = event.get("name")
            if node_name:
                node_str = str(node_name).lower()
                if ":" in node_str:
                    node_str = node_str.split("'")[1]

                # generator: document_type에 따라 렌더링 분기
                #   chat    → answer를 왼쪽 채팅에만 표시
                #   보고서  → chat_message 왼쪽 + answer 오른쪽 보고서 패널
                if node_str == "generator":
                    output = event.get("data", {}).get("output") or {}
                    chat_message = output.get("chat_message", "")
                    answer = output.get("answer", "")
                    if not answer:
                        return []

                    is_report = self._is_report_json(answer)
                    if is_report:
                        results = []
                        if chat_message:
                            results.append((f"__counselor__:{chat_message}", False))
                        results.append((f"__report__:{answer}", False))
                        return results
                    else:
                        return [(f"__counselor__:{answer}", False)]

                # counselor: 다음 질문 (왼쪽 AI 말풍선)
                elif node_str == "counselor":
                    output = event.get("data", {}).get("output") or {}
                    question = output.get("counselor_question")
                    if question:
                        return [(f"__counselor__:{question}", False)]

                # evaluator: 평가 결과 상태 뱃지
                elif node_str == "evaluator":
                    output = event.get("data", {}).get("output") or {}
                    evaluation_response = output.get("evaluation_response")
                    retry_count = output.get("retry_count", 0)

                    if evaluation_response:
                        is_safe = getattr(evaluation_response, "is_secured", True)
                        is_grounded = getattr(evaluation_response, "is_grounded", True)

                        if not is_safe:
                            return [("⚠️ 보안 검증 실패: 검토자에게 전달됩니다.", False)]
                        elif not is_grounded:
                            if retry_count < 3:
                                return [(f"🔄 재생성 중... (시도 {retry_count + 1}/3)", False)]
                            else:
                                return [("⚠️ 최대 재시도 횟수 초과: 검토자에게 전달됩니다.", False)]
                        else:
                            return [("✅ 평가 통과!", False)]

        return []
