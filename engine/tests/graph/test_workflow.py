import pytest
from unittest.mock import MagicMock, patch
from engine.graph.workflow import GraphEngine
from engine.graph.schema import NodeType, PlannerResponse
from engine.graph.state import AgentState, StateKey
from engine.graph.schema import (
    NodeType,
    HumanAction,
    EvaluationResponse,
    HumanFeedback,
    PlannerResponse,
    EvaluationResponse,
    HumanFeedback,
)


class TestGraphEngine:

    @pytest.fixture
    def engine(self):
        """파일 시스템 의존성 없이 엔진 초기화"""
        with patch(
            "engine.graph.utils.AgentSpecLoader.load_yaml", return_value={"test_v1": {}}
        ), patch(
            "engine.graph.utils.AgentSpecLoader.load_elements", return_value="dummy"
        ):
            # 실제 LLM은 사용하지 않으므로 None이나 가짜 객체를 넘깁니다.
            return GraphEngine(llm=MagicMock(), version="test_v1")

    def test_workflow_interruption(self, engine):
        """실제 스키마 객체를 사용하여 흐름 테스트 (Interruption 확인)"""
        thread_id = "thread_1"
        config = engine._configurable(thread_id)

        # MagicMock 대신 실제 클래스 인스턴스를 사용 (직렬화 에러 방지)
        # 각 클래스에 인자가 필요하다면 적절한 기본값을 넣으세요.
        dummy_planner_res = PlannerResponse(
            intention="", node_stack=[], refined_query=""
        )
        dummy_eval_res = EvaluationResponse(probability=0.0, label=1)

        with patch(
            "engine.graph.nodes.planner.Planner.__call__",
            return_value={StateKey.PLANNER_RESPONSE: dummy_planner_res},
        ), patch(
            "engine.graph.nodes.dispatcher.Dispatcher.__call__",
            return_value={StateKey.NEXT_NODE: NodeType.GENERATOR},
        ), patch(
            "engine.graph.nodes.generator.Generator.__call__", return_value={}
        ), patch(
            "engine.graph.nodes.evaluator.Evaluator.__call__",
            return_value={
                StateKey.NEXT_NODE: NodeType.HUMAN_REVIEWER,
                StateKey.EVALUATION_RESPONSE: dummy_eval_res,
            },
        ):

            engine.run(thread_id, "테스트 질문")

        state = engine._app.get_state(config)
        assert NodeType.HUMAN_REVIEWER in state.next

    def test_resume_workflow(self, engine):
        thread_id = "thread_resume_final"
        config = engine._configurable(thread_id)

        # 1. StateManager의 _get 검사를 통과하기 위한 '필수 데이터 풀세트'
        # 프로젝트의 StateManager 정의에 따라 @property로 호출되는 모든 키를 넣어야 합니다.
        initial_state = {
            StateKey.QUERY: "test query",
            StateKey.ANSWER: "테스트 답변",
            StateKey.PLANNER_RESPONSE: PlannerResponse(
                intention="", node_stack=[], refined_query=""
            ),
            # 라우터 route_after_evaluator가 이 값을 찾으므로 반드시 필요!
            StateKey.EVALUATION_RESPONSE: EvaluationResponse(probability=0.0, label=1),
            # resume 후 루프를 방지하기 위해 END_NODE로 설정하거나
            # 혹은 Human Reviewer 이후의 목적지를 설정
            StateKey.NEXT_NODE: NodeType.END_NODE,
        }

        # 상태 주입
        engine._app.update_state(config, initial_state)

        # 2. Resume 실행
        feedback = HumanFeedback(content="좋아요", human_action=HumanAction.APPROVE)

        # resume 시 노드들이 실행되는 것을 방지하기 위해 patch (side_effect로 빈 dict 반환)
        # 특히 Evaluator와 Router가 실행될 때 에러가 나지 않도록 감쌉니다.
        with patch(
            "engine.graph.nodes.evaluator.Evaluator.__call__", return_value={}
        ), patch(
            "engine.graph.nodes.generator.Generator.__call__", return_value={}
        ), patch(
            "engine.graph.nodes.planner.Planner.__call__", return_value={}
        ):

            # 여기서 에러가 발생하지 않아야 함
            engine.resume(thread_id, feedback)

        # 3. 결과 검증
        state = engine._app.get_state(config)

        # 피드백이 상태에 잘 들어갔는지 확인
        stored_feedback = state.values.get(StateKey.HUMAN_FEEDBACK)
        assert stored_feedback is not None
        assert stored_feedback.content == "좋아요"
        assert stored_feedback.human_action == HumanAction.APPROVE
