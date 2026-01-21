from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from typing import TypeVar, Generic, Type, Any, cast
from abc import abstractmethod, ABC
from pydantic import BaseModel
import traceback

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, PlannerResponse, HumanFeedback
from ..utils import AgentSpecLoader
from ...error.errors import SecurityError
from ..logger import logger


class BaseNode(ABC):
    def __init__(self, node_type: NodeType):
        self.key = node_type

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        try:
            return await self._run(state)
        except SecurityError as se:
            logger.warning(f"[Security Alert] {self.key}: {str(se)}")
            return self._create_error_response(str(se))
        except Exception as e:
            logger.error(f"[Node Error] {self.key} | Error: {str(e)}", exc_info=True)
            return self._create_error_response(str(e))

    @abstractmethod
    async def _run(self, state: AgentState) -> dict:
        raise NotImplementedError(
            f"Subclasses of {self.key} must implement the 'run' method."
        )

    def _create_success_response(
        self, messages: list = [], update_dict: dict = {}
    ) -> dict:
        return {StateKey.MESSAGES: messages, StateKey.ERRORS: None, **update_dict}

    def _create_error_response(self, error_msg: str) -> dict:
        return {StateKey.ERRORS: error_msg}


P = TypeVar("P", bound=BaseModel)


class ToolNode(BaseNode, Generic[P]):
    def __init__(self, node_type: NodeType, arg_schema: Type[P], llm: BaseChatModel):
        self.key = node_type
        self.arg_schema = arg_schema
        self.spec = AgentSpecLoader.load_yaml(self.key)
        self.argument_generator = llm.with_structured_output(arg_schema)

        self.prompt_template = AgentSpecLoader.load_tool_argument_prompt(self.key)

    async def _run(self, state: AgentState) -> dict:
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

        return self._create_success_response(
            update_dict={
                StateKey.RETRIEVED_DOCS: {self.key: search_result},
                StateKey.VERIFIER_TARGET_NODE: self.key,
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
