from typing import TypedDict, Annotated, List, Optional, Any, TypeVar, Type, cast
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator
from enum import StrEnum
from pydantic import BaseModel

from .schema import (
    NodeType,
    HumanFeedback,
    PlannerResponse,
    EvaluationResponse,
    CircuitCheck,
)


RetrievedValue = list[dict] | dict | str


def merge_docs(existing: dict | None, new: dict | None) -> dict:
    existing = existing or {}
    if new is None:
        return existing
    if not isinstance(new, dict):
        return existing
    return {**existing, **new}


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
    api_args: Annotated[dict[str, dict], merge_docs]


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
    API_ARGS = "api_args"


T = TypeVar("T")


class StateManager:

    def __init__(self, state: AgentState):
        self._state = state

    _TYPE_MAP: dict[str, Type[BaseModel]] = {
        StateKey.PLANNER_RESPONSE: PlannerResponse,
        StateKey.CIRCUIT_CHECK: CircuitCheck,
        StateKey.HUMAN_FEEDBACK: HumanFeedback,
        StateKey.EVALUATION_RESPONSE: EvaluationResponse,
    }

    def _get_as_model(self, key: str) -> Any:
        """딕셔너리 데이터를 매핑 테이블에 정의된 파이댄틱 모델로 변환"""
        raw_data = self._state.get(key)

        if raw_data is None:
            return None

        model_cls = self._TYPE_MAP.get(key)

        if model_cls:
            if isinstance(raw_data, dict):
                return model_cls.model_validate(raw_data)
            return raw_data

        return raw_data

    @property
    def messages(self) -> List[BaseMessage]:
        return self._state.get(StateKey.MESSAGES, []).copy()

    @property
    def errors(self) -> str:
        return self._state.get(StateKey.ERRORS, "")

    @property
    def query(self) -> str:
        return self._state.get(StateKey.QUERY, "")

    @property
    def planner_response(self) -> PlannerResponse:
        return cast(PlannerResponse, self._get_as_model(StateKey.PLANNER_RESPONSE))

    @property
    def refined_query(self) -> str:
        return (
            self.planner_response.refined_query
            if self.planner_response and self.planner_response.refined_query
            else ""
        )

    @property
    def next_node(self) -> NodeType:
        val = self._state.get(StateKey.NEXT_NODE)
        if val is None:
            raise ValueError("next_node is None.")
        return NodeType(val)

    @property
    def target_node(self) -> NodeType:
        val = self._state.get(StateKey.VERIFIER_TARGET_NODE)
        if val is None:
            raise ValueError("target_node is None.")
        return NodeType(val)

    @property
    def circuit_check(self) -> CircuitCheck:
        obj: CircuitCheck | None = self._get_as_model(StateKey.CIRCUIT_CHECK)
        return obj if obj else CircuitCheck.initialize()

    @property
    def human_feedback(self) -> HumanFeedback:
        obj: HumanFeedback | None = self._get_as_model(StateKey.HUMAN_FEEDBACK)
        if obj is not None:
            hf: HumanFeedback = cast(HumanFeedback, obj)
            return hf
        else:
            return HumanFeedback(content="", human_action=None)

    @property
    def feedback(self) -> str:
        hf: HumanFeedback | None = self.human_feedback
        return hf.content if hf and hf.content else ""

    @property
    def is_verified(self) -> bool:
        return self._state.get(StateKey.IS_VERIFIED, False)

    @property
    def evaluation_response(self) -> EvaluationResponse:
        return cast(
            EvaluationResponse, self._get_as_model(StateKey.EVALUATION_RESPONSE)
        )

    @property
    def answer(self) -> str:
        return self._state.get(StateKey.ANSWER, "")

    @property
    def retrieved_docs(self) -> dict[str, RetrievedValue]:
        return self._state.get(StateKey.RETRIEVED_DOCS, {}).copy()

    @property
    def api_args(self) -> dict[str, dict]:
        return self._state.get(StateKey.API_ARGS, {}).copy()
