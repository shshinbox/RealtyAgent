from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from ..state import AgentState, StateKey, StateManager, RetrievedValue
from ..schema import NodeType, PlannerResponse, CircuitCheck
from .base import BaseNode
from ...security.guard import PromptGuard
from ...error.errors import SecurityError

from typing import cast


class Verifier(BaseNode):
    def __init__(self) -> None:
        self.key = NodeType.VERIFIER

    async def _run(self, state: AgentState) -> dict:
        sm: StateManager = StateManager(state)
        target: NodeType | None = sm.target_node
        if not target:
            raise ValueError("target_node is None.")
        circuit_check: CircuitCheck = sm.circuit_check
        target_doc = sm.retrieved_docs.get(target)

        check_tool_message = ToolMessage(
            content=f"검색 문서: {target_doc}", tool_call_id=f"call_{target}"
        )
        doc_length = self.doc_len(target_node=target, target_doc=target_doc)

        guard_prompt: PromptGuard = PromptGuard()
        _is_secured = await guard_prompt.is_secured([check_tool_message])

        is_verified: bool = doc_length > 0 and not sm.errors and _is_secured

        new_circuit_check: CircuitCheck | None = None

        if not is_verified:
            new_circuit_check = circuit_check.increase(target)

        return self._create_success_response(
            update_dict={
                StateKey.IS_VERIFIED: is_verified,
                StateKey.CIRCUIT_CHECK: (
                    new_circuit_check if new_circuit_check is not None else circuit_check
                ),
            },
        )

    def doc_len(self, target_node: NodeType, target_doc):
        if target_node == NodeType.LEGAL_RETRIEVER and isinstance(target_doc, dict):
            return len(target_doc.get("Expc", []))
        return 0
