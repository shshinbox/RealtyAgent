import pytest
from engine.graph.schema import NodeType, HumanAction, EvaluationResponse, HumanFeedback
from engine.graph.state import StateKey, AgentState
from typing import cast
from engine.graph.router import (
    route_after_dispatcher,
    route_after_verifier,
    route_after_evaluator,
    route_after_human,
)


class TestRouterLogic:

    def test_route_after_dispatcher(self):
        """Dispatcher 결과에 따른 노드 전환 테스트"""
        state = cast(AgentState, {StateKey.NEXT_NODE: NodeType.LEGAL_RETRIEVER})
        assert route_after_dispatcher(state) == NodeType.LEGAL_RETRIEVER

    def test_route_after_verifier(self):
        """Verifier 검증 결과에 따른 루프/진행 테스트"""
        # Case 1: 검증 실패 시 해당 노드로 다시 돌아감 (Retry)
        fail_state = cast(
            AgentState,
            {
                StateKey.IS_VERIFIED: False,
                StateKey.VERIFIER_TARGET_NODE: NodeType.LEGAL_RETRIEVER,
            },
        )
        assert route_after_verifier(fail_state) == NodeType.LEGAL_RETRIEVER

        # Case 2: 검증 성공 시 다시 Dispatcher로 이동 (Next Task)
        success_state = cast(
            AgentState,
            {
                StateKey.IS_VERIFIED: True,
                StateKey.VERIFIER_TARGET_NODE: NodeType.LEGAL_RETRIEVER,
            },
        )
        assert route_after_verifier(success_state) == NodeType.DISPATCHER

    def test_route_after_evaluator(self):
        """Evaluator 결과(최종 답변 품질)에 따른 분기 테스트"""
        # Case 1: Label이 1이면 Human Review로 이동
        review_state = cast(
            AgentState,
            {
                StateKey.EVALUATION_RESPONSE: EvaluationResponse(
                    probability=0.0, label=1
                )
            },
        )
        assert route_after_evaluator(review_state) == NodeType.HUMAN_REVIEWER

        # Case 2: Label이 0이면 종료
        end_state = cast(
            AgentState,
            {
                StateKey.EVALUATION_RESPONSE: EvaluationResponse(
                    probability=0.0, label=0
                )
            },
        )
        assert route_after_evaluator(end_state) == NodeType.END_NODE

    def test_route_after_human(self):
        """사용자 피드백(HumanAction)에 따른 워크플로우 제어 테스트"""

        # 1. REPLAN 선택 시 -> 다시 Planner로
        replan_fb = HumanFeedback(content="다시 짜줘", human_action=HumanAction.REPLAN)
        replan_fb.set_human_action(HumanAction.REPLAN)
        replan_state = cast(AgentState, {StateKey.HUMAN_FEEDBACK: replan_fb})
        assert route_after_human(replan_state) == NodeType.PLANNER

        # 2. REWRITE 선택 시 -> 다시 Generator로
        rewrite_fb = HumanFeedback(
            content="말투만 고쳐줘", human_action=HumanAction.REWRITE
        )
        rewrite_fb.set_human_action(HumanAction.REWRITE)
        rewrite_state = cast(AgentState, {StateKey.HUMAN_FEEDBACK: rewrite_fb})
        assert route_after_human(rewrite_state) == NodeType.GENERATOR

        # 3. APPROVE 선택 시 -> 종료
        approve_fb = HumanFeedback(content="좋아", human_action=HumanAction.APPROVE)
        approve_fb.set_human_action(HumanAction.APPROVE)
        approve_state = cast(AgentState, {StateKey.HUMAN_FEEDBACK: approve_fb})
        assert route_after_human(approve_state) == NodeType.END_NODE
