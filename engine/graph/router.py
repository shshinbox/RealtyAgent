from .schema import (
    NodeType,
    HumanFeedback,
    EvaluationResponse,
    HumanAction,
    CircuitCheck,
)
from .state import AgentState, StateManager


def route_after_dispatcher(state: AgentState) -> NodeType | None:
    sm: StateManager = StateManager(state=state)
    return sm.next_node


def route_after_verifier(state: AgentState) -> NodeType:
    sm: StateManager = StateManager(state=state)
    is_verified: bool = sm.is_verified
    target_node: NodeType = sm.target_node
    circuit_limit: CircuitCheck = sm.circuit_check

    next_node: NodeType | None = None

    if not is_verified:
        next_node = target_node

    if circuit_limit.is_over_limit(target_node):
        next_node = NodeType.DISPATCHER

    return next_node or NodeType.DISPATCHER


def route_after_evaluator(state: AgentState) -> NodeType:
    sm: StateManager = StateManager(state=state)

    # Evaluator에서 next_node를 명시적으로 설정했다면 그것을 따름
    # (재시도 또는 Human Reviewer로)
    if sm.next_node:
        return sm.next_node

    # next_node가 없으면 검증 통과 → DISPATCHER로 돌아가 최종 결정
    return NodeType.DISPATCHER


def route_after_human(state: AgentState) -> NodeType:
    sm: StateManager = StateManager(state=state)
    human_feedback: HumanFeedback = sm.human_feedback
    answer: str = sm.answer

    match human_feedback.human_action:
        case HumanAction.REPLAN:
            return NodeType.PLANNER
        case HumanAction.REWRITE:
            return NodeType.GENERATOR
        case HumanAction.APPROVE:
            return NodeType.DISPATCHER

        case _:
            raise ValueError(f"Unknown action: {human_feedback.human_action}")
