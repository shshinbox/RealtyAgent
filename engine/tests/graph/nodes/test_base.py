import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
from engine.graph.nodes.base import ToolNode, LLMNode
from engine.graph.state import StateManager, AgentState, StateKey
from engine.graph.schema import NodeType
from engine.graph.nodes.dispatcher import Dispatcher


class MockSchema(BaseModel):
    query: str


class TestToolNode(ToolNode[MockSchema]):
    def _execute_tool(self, args: MockSchema) -> dict:
        return {"result": f"processed {args.query}"}


class TestLLMNode(LLMNode[MockSchema]):
    def _run(self, state: AgentState) -> dict:
        res = self._ask_llm("prompt")
        return self._create_success_response(messages=[], update_dict={"data": res})


class TestBaseNodes:
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.with_structured_output.return_value = llm
        return llm

    def test_tool_node_full_flow(self, mock_llm):
        """ToolNode의 전체 흐름을 테스트하며 실제 발생한 에러를 캡처함"""

        with patch("engine.graph.nodes.base.AgentSpecLoader") as MockLoader, patch(
            "engine.graph.nodes.base.StateManager"
        ) as MockManager:

            # Setup
            MockLoader.load_tool_argument_prompt.return_value = (
                "Template {query} {feedback}"
            )
            MockLoader.load_yaml.return_value = {}

            sm = MockManager.return_value
            sm.planner_response = None
            sm.query = "테스트 질문"
            sm.human_feedback_or_none = None

            # LLM 응답 설정
            mock_llm.invoke.return_value = MockSchema(query="추출된 쿼리")

            node = TestToolNode(NodeType.LEGAL_RETRIEVER, MockSchema, mock_llm, "v1")
            result = node(state={})

            # --- DEBUG BLOCK: 여기서 진짜 에러를 알려줍니다 ---
            if StateKey.ERRORS in result and result[StateKey.ERRORS]:
                # 에러 내용을 터미널에 강제로 출력하고 테스트 실패 처리
                pytest.fail(f"실제 노드 내부 에러 발생: {result[StateKey.ERRORS]}")
            # ----------------------------------------------

            assert result[StateKey.RETRIEVED_DOCS][NodeType.LEGAL_RETRIEVER] == {
                "result": "processed 추출된 쿼리"
            }

    def test_llm_node_error_handling(self, mock_llm):
        """LLMNode에서 예외 발생 시 에러 응답 반환 테스트"""

        with patch("engine.graph.nodes.base.AgentSpecLoader") as MockLoader:
            MockLoader.load_prompt.return_value = "Prompt"

            # LLM 에러 시뮬레이션
            mock_llm.invoke.side_effect = Exception("LLM 파손")

            node = TestLLMNode(NodeType.PLANNER, MockSchema, mock_llm, "v1")
            result = node(state={})

            # 검증: 에러가 raise되지 않고 dict로 반환되는지 확인
            assert result[StateKey.ERRORS] == "LLM 파손"

    def test_tool_node_invalid_type_check(self, mock_llm):
        """LLM이 엉뚱한 타입을 반환했을 때 TypeError 발생 여부 테스트"""

        with patch("engine.graph.nodes.base.AgentSpecLoader") as MockLoader, patch(
            "engine.graph.nodes.base.StateManager"
        ) as MockManager:

            MockLoader.load_tool_argument_prompt.return_value = "Template"
            mock_llm.invoke.return_value = {
                "not": "a_pydantic_model"
            }  # 잘못된 타입 반환

            node = TestToolNode(NodeType.LEGAL_RETRIEVER, MockSchema, mock_llm, "v1")

            # TypeError가 실제로 발생하는지 확인
            with pytest.raises(TypeError) as excinfo:
                node(state={})

            assert "LLM returned an invalid type" in str(excinfo.value)
