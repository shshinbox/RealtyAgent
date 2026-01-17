import pytest
from unittest.mock import MagicMock, patch
from engine.graph.nodes.legal_retriever import LegalRetriever
from engine.graph.schema import LegalSearchQuery
from engine.graph.state import StateKey


@patch("engine.graph.nodes.legal_retriever.requests")
@patch("engine.graph.nodes.legal_retriever.AgentSpecLoader")  # 1. 자식 모듈 패치
@patch("engine.graph.nodes.base.AgentSpecLoader")  # 2. 부모 모듈 패치
def test_legal_retriever_execute_tool(MockBaseLoader, MockLocalLoader, MockRequests):
    # 두 Mock 객체에 동일한 설정 적용
    for loader in [MockBaseLoader, MockLocalLoader]:
        loader.load_tool_argument_prompt.return_value = "dummy prompt"
        loader.load_elements.return_value = "https://api.law.go.kr/test"

    # API Mock 설정
    mock_response = MagicMock()
    mock_response.json.return_value = {"totalCount": "1", "items": [{"title": "판례1"}]}
    mock_response.status_code = 200
    MockRequests.get.return_value = mock_response

    # 실행
    args = LegalSearchQuery(keyword="임대차보호법", search=2, itmno="123456")
    retriever = LegalRetriever(llm=MagicMock(), version="v1")
    result = retriever._execute_tool(args)

    # 검증
    assert result["totalCount"] == "1"


def test_legal_retriever_error_handling():
    # 함수 내부에서 필요한 모든 것을 한 번에 패치
    with patch("engine.graph.nodes.base.StateManager") as MockManager, patch(
        "engine.graph.nodes.base.AgentSpecLoader"
    ) as MockBaseLoader, patch(
        "engine.graph.nodes.legal_retriever.AgentSpecLoader"
    ) as MockLocalLoader, patch(
        "engine.graph.nodes.legal_retriever.requests"
    ) as MockRequests:

        # Mock 공통 설정
        for l in [MockBaseLoader, MockLocalLoader]:
            l.load_elements.return_value = "http://test.com"
            l.load_tool_argument_prompt.return_value = "prompt"

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_llm.invoke.return_value = LegalSearchQuery(keyword="test")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Server Error")
        MockRequests.get.return_value = mock_response

        retriever = LegalRetriever(llm=mock_llm, version="v1")
        result = retriever({})

        assert result[StateKey.ERRORS] == "API Server Error"
