from typing import Any, TypedDict, Optional, List, Final
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import StrEnum, auto


class NodeType(StrEnum):
    INITIALIZER = auto()
    PLANNER = auto()
    DISPATCHER = auto()
    HUMAN_REVIEWER = auto()
    LEGAL_RETRIEVER = auto()
    DOC_RETRIEVER = auto()
    VERIFIER = auto()
    GENERATOR = auto()
    EVALUATOR = auto()
    FINALIZER = auto()


class PlannerResponse(BaseModel):
    refined_query: Optional[str] = Field(description="사용자 쿼리의 개선된 버전")
    intention: Optional[str] = Field(description="사용자의 의도 요약")
    node_stack: list[NodeType] = Field(default=[], description="호출할 노드 리스트")

    def is_exhausted(self) -> bool:
        return not self.node_stack

    def pop_stack(self) -> NodeType:
        if not self.node_stack:
            raise ValueError("node_stack is empty.")
        next_node = self.node_stack[0]
        self.node_stack = self.node_stack[1:]
        return next_node

    def current_node(self) -> NodeType:
        if not self.node_stack:
            raise ValueError("node_stack is empty.")
        return self.node_stack[0]


class HumanAction(StrEnum):
    REPLAN = auto()
    REWRITE = auto()
    APPROVE = auto()


class HumanFeedback(BaseModel):
    content: Optional[str] = Field(description="사용자 피드백 정보")
    human_action: Optional[HumanAction] = Field(description="사용자의 다음 요청")

    def set_human_action(self, action: HumanAction):
        self.human_action = action


class HumanFeedbackResponse(BaseModel):
    action: HumanAction = Field(description="사용자의 피드백 분석 결과")


class LegalSearchQuery(BaseModel):
    keyword: str = Field(description="검색 키워드")
    search: int = Field(
        default=1, description="검색범위 (기본 : 1 법령해석례명) 2 : 본문검색"
    )
    inq: str | None = Field(default=None, description="질의기관")
    rpl: str | None = Field(default=None, description="회신기관")
    gana: str | None = Field(default=None, description="사전식 검색(ga,na,da…,etc)")
    itmno: str | None = Field(
        default=None, description="안건번호 13-0217 검색을 원할 경우 itmno=130217"
    )
    regYd: str | None = Field(
        default=None, description="등록일자 검색(20090101~20090130)"
    )
    explYd: str | None = Field(
        default=None, description="해석일자 검색(20090101~20090130)"
    )


class DocumentSearchQuery(BaseModel):
    query: str


class EvaluationResponse(BaseModel):
    is_secured: bool = Field(description="프롬프트 공격 여부")
    is_grounded: bool = Field(description="환각 여부")
    has_pii: bool = Field(description="개인정보 포함 여부")

    def is_safe(self):
        return self.is_secured and self.is_grounded and not self.has_pii


class CircuitCheck(BaseModel):
    circuit_stat: dict[NodeType, int]
    LIMIT: int = 3

    @classmethod
    def initialize(cls):
        return cls(
            circuit_stat={
                NodeType.LEGAL_RETRIEVER: 0,
                NodeType.DOC_RETRIEVER: 0,
            }
        )

    def is_over_limit(self, node_type: NodeType) -> bool:
        return self.circuit_stat.get(node_type, 0) >= self.LIMIT

    def increase(self, node_type: NodeType) -> "CircuitCheck":
        new_stat = self.circuit_stat.copy()
        new_stat[node_type] = new_stat.get(node_type, 0) + 1
        return self.model_copy(update={"circuit_stat": new_stat})

    def get_count(self, node_type: NodeType) -> int:
        return self.circuit_stat.get(node_type, 0)


class GeneratorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(description="사용자의 질문에 대한 최종 답변 텍스트")
