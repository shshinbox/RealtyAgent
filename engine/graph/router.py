from .schema import (
    NodeType,
    HumanFeedback,
    EvaluationResponse,
    HumanAction,
)
from .state import AgentState, StateManager


def route_after_dispatcher(state: AgentState) -> NodeType | None:
    sm: StateManager = StateManager(state=state)
    return sm.next_node


def _route_after_retriever(state: AgentState, node_type: NodeType) -> NodeType:
    sm: StateManager = StateManager(state=state)
    if sm.is_verified or sm.circuit_check.is_over_limit(node_type):
        return NodeType.DISPATCHER
    return node_type


def route_after_legal_retriever(state: AgentState) -> NodeType:
    return _route_after_retriever(state, NodeType.LEGAL_RETRIEVER)


def route_after_doc_retriever(state: AgentState) -> NodeType:
    return _route_after_retriever(state, NodeType.DOC_RETRIEVER)


def route_after_evaluator(state: AgentState) -> NodeType:
    sm: StateManager = StateManager(state=state)

    # Evaluator에서 next_node를 명시적으로 설정했다면 그것을 따름
    # (재시도 또는 Human Reviewer로)
    if sm.next_node:
        return sm.next_node

    # next_node가 없으면 검증 통과 → DISPATCHER로 돌아가 최종 결정
    return NodeType.DISPATCHER


def route_after_counselor(state: AgentState) -> NodeType:
    sm: StateManager = StateManager(state=state)
    if sm.consultation_context.is_ready:
        return NodeType.DISPATCHER
    return NodeType.COUNSELOR


def route_after_human(state: AgentState) -> NodeType:
    sm: StateManager = StateManager(state=state)
    human_feedback: HumanFeedback = sm.human_feedback

    match human_feedback.human_action:
        case HumanAction.REPLAN:
            return NodeType.PLANNER
        case HumanAction.REWRITE:
            return NodeType.GENERATOR
        case HumanAction.APPROVE:
            return NodeType.DISPATCHER

        case _:
            raise ValueError(f"Unknown action: {human_feedback.human_action}")
