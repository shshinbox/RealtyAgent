from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from ..state import AgentState, StateKey, StateManager, RetrievedValue
from ..schema import NodeType, PlannerResponse, CircuitCheck
from .base import BaseNode
from ..tools import GuardPrompt
from ...error.errors import SecurityError

from typing import cast


class Verifier(BaseNode):
    def __init__(self) -> None:
        self.key = NodeType.VERIFIER

    def _run(self, state: AgentState) -> dict:
        sm: StateManager = StateManager(state)
        target: NodeType = sm.target_node
        circuit_check: CircuitCheck = sm.circuit_check
        target_doc = sm.retrieved_docs.get(target)

        check_tool_message = ToolMessage(
            content=f"검색 문서: {target_doc}", tool_call_id=f"call_{target}"
        )
        doc_length = self.doc_len(target_node=target, target_doc=target_doc)

        guard_prompt: GuardPrompt = GuardPrompt()

        is_verified: bool = (
            doc_length > 0
            and not sm.errors
            and guard_prompt.is_secured([check_tool_message])
        )

        new_circuit_check: CircuitCheck | None = None

        if not is_verified:
            new_circuit_check = circuit_check.increase(target)

        return self._create_success_response(
            update_dict={
                StateKey.IS_VERIFIED: is_verified,
                StateKey.CIRCUIT_CHECK: new_circuit_check or circuit_check,
            },
        )

    def doc_len(self, target_node: NodeType, target_doc):
        if target_node == NodeType.LEGAL_RETRIEVER:
            return len(target_doc.get("Expc", []))
        return 0
