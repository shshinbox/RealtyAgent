from typing import TypedDict, Annotated, List, Optional, Any, TypeVar, Type, cast
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator
from enum import StrEnum

from .schema import (
    NodeType,
    HumanFeedback,
    PlannerResponse,
    EvaluationResponse,
    CircuitCheck,
)


RetrievedValue = list[dict] | dict | str


class AgentState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]
    errors: Optional[str]
    query: Optional[str]
    planner_response: Optional[PlannerResponse]
    next_node: Optional[NodeType]
    verifier_target_node: Optional[NodeType]
    circuit_check: Optional[CircuitCheck]
    human_feedback: Optional[HumanFeedback]
    is_verified: Optional[bool]
    evaluation_response: Optional[EvaluationResponse]
    answer: Optional[str]
    retrieved_docs: Annotated[dict[str, RetrievedValue], merge_docs]


def merge_docs(existing: dict, new: dict) -> dict:
    return {**existing, **new}


class StateKey(StrEnum):
    MESSAGES = "messages"
    ERRORS = "errors"
    QUERY = "query"
    PLANNER_RESPONSE = "planner_response"
    NEXT_NODE = "next_node"
    VERIFIER_TARGET_NODE = "verifier_target_node"
    CIRCUIT_CHECK = "circuit_check"
    HUMAN_FEEDBACK = "human_feedback"
    IS_VERIFIED = "is_verified"
    EVALUATION_RESPONSE = "evaluation_response"
    ANSWER = "answer"
    RETRIEVED_DOCS = "retrieved_docs"


T = TypeVar("T")


class StateManager:
    def __init__(self, state: AgentState):
        self._state = state

    def _get(self, key: str, expected_type: Type[T]) -> T:
        value = self._state.get(key)
        if value is None:
            raise ValueError(f"{key} is missing.")
        if not isinstance(value, expected_type):
            raise TypeError(f"{key} type mismatch.")
        return cast(T, value)

    @property
    def messages(self) -> List[BaseMessage]:
        return self._state.get(StateKey.MESSAGES, [])

    @property
    def errors(self) -> str:
        return self._state.get(StateKey.ERRORS, "")

    @property
    def query(self) -> str:
        return self._get(StateKey.QUERY, str)

    @property
    def planner_response(self) -> PlannerResponse:
        return self._get(StateKey.PLANNER_RESPONSE, PlannerResponse)

    @property
    def refined_query(self) -> str:
        pr: PlannerResponse = self._state.get(StateKey.PLANNER_RESPONSE, None)
        return (pr and pr.refined_query) or ""

    @property
    def next_node(self) -> NodeType:
        return self._get(StateKey.NEXT_NODE, NodeType)

    @property
    def target_node(self) -> NodeType:
        return self._get(StateKey.VERIFIER_TARGET_NODE, NodeType)

    @property
    def circuit_check(self) -> CircuitCheck:
        return self._state.get(StateKey.CIRCUIT_CHECK, CircuitCheck.initialize())

    @property
    def human_feedback(self) -> HumanFeedback:
        return self._get(StateKey.HUMAN_FEEDBACK, HumanFeedback)

    @property
    def feedback(self) -> str:
        hf: HumanFeedback = self._state.get(StateKey.HUMAN_FEEDBACK, None)
        return (hf and hf.content) or ""

    @property
    def is_verified(self) -> bool:
        return self._state.get(StateKey.IS_VERIFIED, False)

    @property
    def evaluation_response(self) -> EvaluationResponse:
        return self._get(StateKey.EVALUATION_RESPONSE, EvaluationResponse)

    @property
    def answer(self) -> str:
        return self._get(StateKey.ANSWER, str)

    @property
    def retrieved_docs(self) -> dict[str, RetrievedValue]:
        return self._state.get(StateKey.RETRIEVED_DOCS, {})
