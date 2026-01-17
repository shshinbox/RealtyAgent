import pytest
from unittest.mock import MagicMock, patch
from engine.graph.nodes.human_reviewer import HumanReviewer
from engine.graph.schema import NodeType, HumanAction
from engine.graph.state import StateKey
from langchain_core.messages import HumanMessage


@patch("engine.graph.nodes.human_reviewer.StateManager")
@patch("engine.graph.nodes.base.AgentSpecLoader")
def test_human_reviewer_run(MockLoader, MockManager):
    # 1. Setup: LLM 및 Mock 객체 설정
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_llm

    # LLM이 결정할 행동(Action) 모킹
    expected_action = HumanAction.APPROVE
    mock_llm.invoke.return_value = expected_action

    # HumanFeedback 객체 모킹
    mock_feedback = MagicMock()
    mock_feedback.content = "좋아, 계속 진행해줘"

    # StateManager가 위 피드백을 반환하도록 설정
    sm_instance = MockManager.return_value
    sm_instance.human_feedback = mock_feedback

    # 노드 생성 (LLMNode 상속 구조 반영)
    reviewer = HumanReviewer(llm=mock_llm, version="v1")

    # 2. 실행
    # 실제 state 딕셔너리는 내부에서 매니저가 처리하므로 빈 값 전달
    result = reviewer(state={})

    # 3. 검증 (Assertion)
    # A. LLM 결과가 피드백 객체에 반영되었는가?
    mock_feedback.set_human_action.assert_called_once_with(expected_action)

    # B. 결과 딕셔너리에 업데이트된 피드백이 포함되었는가?
    assert result[StateKey.HUMAN_FEEDBACK] == mock_feedback

    # C. 성공 메시지가 생성되었는가?
    assert isinstance(result[StateKey.MESSAGES][0], HumanMessage)
    assert "사용자 피드백 처리 완료" in result[StateKey.MESSAGES][0].content

    # D. 에러 필드가 None인가?
    assert result[StateKey.ERRORS] is None
