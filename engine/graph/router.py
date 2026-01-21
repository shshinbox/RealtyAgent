from .schema import (
    NodeType,
    HumanFeedback,
    EvaluationResponse,
    PlannerResponse,
    HumanAction,
    CircuitCheck,
)
from .state import AgentState, StateKey, StateManager


def route_after_dispatcher(state: AgentState) -> NodeType:
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
    evaluation_response: EvaluationResponse = sm.evaluation_response

    if not evaluation_response.is_safe():
        return NodeType.HUMAN_REVIEWER

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
