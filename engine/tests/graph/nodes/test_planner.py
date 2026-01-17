import pytest
from unittest.mock import MagicMock, patch
from engine.graph.nodes.planner import Planner
from engine.graph.schema import NodeType, PlannerResponse, HumanFeedback
from langchain_core.messages import AIMessage
from engine.graph.state import StateKey


class TestPlannerNode:
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.with_structured_output.return_value = llm
        return llm

    def test_planner_run_success(self, mock_llm):
        # 1. Setup: 모듈 경로 주의 (실제 프로젝트 구조에 맞게 수정)
        with patch("engine.graph.nodes.base.AgentSpecLoader") as MockLoader, patch(
            "engine.graph.nodes.planner.StateManager"
        ) as MockManager:

            # 프롬프트 템플릿 설정 (raw_query, human_feedback 인자 포함)
            MockLoader.load_prompt.return_value = (
                "Query: {raw_query}, Feedback: {human_feedback}"
            )

            # StateManager 모킹
            sm = MockManager.return_value
            sm.query = "연세대학교 주변 아파트 매물 찾아줘"
            # feedback이 있는 경우 시뮬레이션
            mock_feedback = MagicMock(spec=HumanFeedback)
            mock_feedback.content = "최근 1개월 이내 실거래가 위주로 보여줘"
            sm.human_feedback = mock_feedback

            # LLM 응답(PlannerResponse) 모킹
            expected_plan = PlannerResponse(
                refined_query="정리된 질문",
                intention="사용자 의도",
                node_stack=[NodeType.LEGAL_RETRIEVER],
            )
            mock_llm.invoke.return_value = expected_plan

            # 2. 실행
            planner_node = Planner(llm=mock_llm, version="v1")
            result = planner_node(state={})

            # 3. 검증
            # A. 결과에 PlannerResponse가 포함되었는가?
            assert result[StateKey.PLANNER_RESPONSE] == expected_plan
            assert result[StateKey.QUERY] == sm.query

            # B. 메시지가 AIMessage 타입으로 생성되었는가?
            assert isinstance(result[StateKey.MESSAGES][0], AIMessage)
            assert "Planner execution" in result[StateKey.MESSAGES][0].content

            # C. 에러 필드가 None인가?
            assert result[StateKey.ERRORS] is None

            # D. 프롬프트 포맷팅이 정상적으로 호출되었는가? (추가 검증)
            MockLoader.load_prompt.assert_called_once()

    def test_planner_run_with_empty_feedback(self, mock_llm):
        """피드백이 없을 때(None)도 빈 문자열로 처리되어 정상 동작하는지 테스트"""
        with patch("engine.graph.nodes.base.AgentSpecLoader") as MockLoader, patch(
            "engine.graph.nodes.planner.StateManager"
        ) as MockManager:

            MockLoader.load_prompt.return_value = "Q: {raw_query}, F: {human_feedback}"

            sm = MockManager.return_value
            sm.query = "강남구 전세 정보"
            sm.human_feedback = None  # 피드백이 없는 상황

            mock_llm.invoke.return_value = PlannerResponse(
                refined_query="정리된 질문",
                intention="사용자 의도",
                node_stack=[NodeType.LEGAL_RETRIEVER],
            )

            planner_node = Planner(llm=mock_llm, version="v1")
            result = planner_node(state={})

            assert result[StateKey.ERRORS] is None
