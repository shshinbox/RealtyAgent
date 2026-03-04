from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, CircuitCheck
from .base import BaseNode
from ...security.guard import PromptGuard

from typing import Any, cast


class Verifier(BaseNode):
    def __init__(self) -> None:
        super().__init__(NodeType.VERIFIER)

    async def _run(self, state: AgentState, _config: RunnableConfig) -> dict:
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
                    new_circuit_check
                    if new_circuit_check is not None
                    else circuit_check
                ),
            },
        )

    def doc_len(self, target_node: NodeType, target_doc: Any) -> int:
        if not target_doc:
            return 0
        
        if target_node == NodeType.LEGAL_RETRIEVER and isinstance(target_doc, dict):
            
            num = target_doc.get("numOfRows")
            if num is None:
                num = target_doc.get("Expc", {}).get("numOfRows")
            expc_list = None
            try:
                expc_list = target_doc.get("Expc", {}).get("expc")
            except Exception:
                expc_list = None

            if isinstance(expc_list, list):
                return len(expc_list)

            if num is not None:
                try:
                    return int(num)
                except Exception:
                    import re

                    s = str(num)
                    m = re.search(r"(\d+)", s)
                    return int(m.group(1)) if m else 0

        if isinstance(target_doc, list):
            return len(target_doc)

        if isinstance(target_doc, str):
            return 1 if target_doc.strip() else 0

        if isinstance(target_doc, dict):
            if "documents" in target_doc and isinstance(target_doc["documents"], list):
                return len(target_doc["documents"])
            return len(target_doc)

        return 0
