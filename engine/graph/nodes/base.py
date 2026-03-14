from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from typing import TypeVar, Generic, Type, Any, cast
from abc import abstractmethod, ABC
from pydantic import BaseModel
import traceback

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, CircuitCheck
from ..utils import AgentSpecLoader
from ...error.errors import SecurityError
from ..logger import logger


class BaseNode(ABC):
    def __init__(self, node_type: NodeType):
        self.key = node_type

    async def __call__(
        self, state: AgentState, config: RunnableConfig
    ) -> dict[str, Any]:
        try:
            return await self._run(state, config)
        except SecurityError as se:
            logger.warning(f"[Security Alert] {self.key}: {str(se)}")
            return self._create_error_response(str(se))
        except Exception as e:
            logger.error(f"[Node Error] {self.key} | Error: {str(e)}", exc_info=True)
            return self._create_error_response(str(e))

    @abstractmethod
    async def _run(self, state: AgentState, config: RunnableConfig) -> dict:
        raise NotImplementedError(
            f"Subclasses of {self.key} must implement the 'run' method."
        )

    def _create_success_response(
        self, messages: list = [], update_dict: dict = {}
    ) -> dict:
        return {StateKey.MESSAGES: messages, StateKey.ERRORS: None, **update_dict}

    def _create_error_response(self, error_msg: str) -> dict:
        return {StateKey.ERRORS: error_msg}

    def _doc_len(self, result: Any) -> int:
        """검색 결과 길이 확인. 서브클래스에서 API 응답 포맷에 맞게 오버라이드 가능."""
        if not result:
            return 0
        if isinstance(result, list):
            return len(result)
        if isinstance(result, str):
            return 1 if result.strip() else 0
        if isinstance(result, dict):
            if "documents" in result and isinstance(result["documents"], list):
                return len(result["documents"])
            return len(result)
        return 0

    async def _validate_retrieved_docs(
        self, result: Any, circuit_check: CircuitCheck
    ) -> tuple[bool, CircuitCheck]:
        """검색 결과 유효성 검사 + circuit breaker 업데이트."""
        from ...security.guard import PromptGuard

        doc_length = self._doc_len(result)
        check_message = ToolMessage(
            content=f"검색 문서: {result}", tool_call_id=f"call_{self.key}"
        )
        is_secured = await PromptGuard().is_secured([check_message])
        is_valid = doc_length > 0 and is_secured
        new_circuit_check = circuit_check.increase(self.key) if not is_valid else circuit_check
        return is_valid, new_circuit_check


P = TypeVar("P", bound=BaseModel)


class ToolNode(BaseNode, Generic[P]):
    def __init__(self, node_type: NodeType, arg_schema: Type[P], llm: BaseChatModel):
        self.key = node_type
        self.arg_schema = arg_schema
        self.spec = AgentSpecLoader.load_yaml(self.key)
        self.argument_generator = llm.with_structured_output(arg_schema)

        self.prompt_template = AgentSpecLoader.load_tool_argument_prompt(self.key)

    async def _run(self, state: AgentState, config: RunnableConfig) -> dict:
        sm: StateManager = StateManager(state=state)
        query: str = sm.refined_query or sm.query
        feedback_content: str = sm.feedback

        formatted_prompt: str = self.prompt_template.format(
            query=query, feedback=feedback_content, api_args=sm.api_args
        )
        raw_response = await self.argument_generator.ainvoke(formatted_prompt)

        if not isinstance(raw_response, self.arg_schema):
            raise TypeError(
                f"LLM returned an invalid type: {type(raw_response)}. "
                f"Expected: {self.arg_schema.__name__}"
            )

        api_args = cast(P, raw_response)
        search_result = await self._execute_tool(api_args)
        is_valid, new_circuit_check = await self._validate_retrieved_docs(
            search_result, sm.circuit_check
        )

        return self._create_success_response(
            update_dict={
                StateKey.RETRIEVED_DOCS: {self.key: search_result},
                StateKey.IS_VERIFIED: is_valid,
                StateKey.CIRCUIT_CHECK: new_circuit_check,
                StateKey.API_ARGS: {self.key: api_args},
            },
        )

    @abstractmethod
    async def _execute_tool(self, args: P) -> dict:
        raise NotImplementedError(
            f"Subclasses of {self.key} must implement the '_execute_tool' method."
        )


T = TypeVar("T")


class LLMNode(BaseNode, Generic[T]):
    def __init__(
        self,
        node_type: NodeType,
        output_type: Type[T],
        llm: BaseChatModel,
    ) -> None:
        self.key = node_type
        self.output_type = output_type
        self.llm = llm.with_structured_output(output_type)
        self.prompt_template = AgentSpecLoader.load_prompt(agent_name=self.key)

    async def _ask_llm(self, prompt: str) -> T:
        result = await self.llm.ainvoke(prompt)
        if isinstance(result, self.output_type):
            return cast(T, result)
        raise TypeError(
            f"LLM failed to return a structured {self.output_type.__name__}."
        )
