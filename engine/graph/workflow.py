from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langchain_core.language_models import BaseChatModel

from .state import AgentState, StateKey
from .router import (
    route_after_dispatcher,
    route_after_verifier,
    route_after_evaluator,
    route_after_human,
)
from .schema import NodeType, HumanFeedback
from .nodes.initialize import Initializer
from .nodes.legal_retriever import LegalRetriever
from .nodes.doc_retriever import DocumentsRetriever
from .nodes.dispatcher import Dispatcher
from .nodes.human_reviewer import HumanReviewer
from .nodes.planner import Planner
from .nodes.verifier import Verifier
from .nodes.generator import Generator
from .nodes.evaluator import Evaluator


class GraphEngine:
    def __init__(self, llm: BaseChatModel, version: str):
        self._memory = MemorySaver()
        self._workflow = self._build_workflow(llm=llm, version=version)
        self._app = self._workflow.compile(
            checkpointer=self._memory, interrupt_before=[NodeType.HUMAN_REVIEWER]
        )

    def run(self, thread_id: str, query: str) -> dict:
        """
        워크플로우를 실행한다.

        Args:
            thread_id: 대화 구분을 위한 세션 ID
            query: 사용자 질문

        Returns:
            AgentState: 최종 상태 결과

        Raises:
            SecurityError: 사용자의 입력에서 직접적인 프롬프트 인젝션이 감지될 때 발생
        """
        config: RunnableConfig = self._configurable(thread_id)
        return self._app.invoke({StateKey.QUERY: query}, config)

    def resume(self, thread_id: str, feedback: HumanFeedback):
        config: RunnableConfig = self._configurable(thread_id)
        self._app.update_state(config, {StateKey.HUMAN_FEEDBACK: feedback})
        return self._app.invoke(None, config)

    def _configurable(self, thread_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": thread_id}}

    def _build_workflow(self, llm: BaseChatModel, version: str) -> StateGraph:
        workflow: StateGraph = StateGraph(AgentState)

        initializer: Initializer = Initializer()
        planner: Planner = Planner(llm=llm, version=version)
        dispatcher: Dispatcher = Dispatcher()
        legal_retriever: LegalRetriever = LegalRetriever(llm=llm, version=version)
        doc_retriever: DocumentsRetriever = DocumentsRetriever(llm=llm, version=version)
        human_reviewer: HumanReviewer = HumanReviewer(llm=llm, version=version)
        verifier: Verifier = Verifier()
        generator: Generator = Generator(llm=llm, version=version)
        evaluator: Evaluator = Evaluator()

        workflow.add_node(NodeType.INITIALIZER, initializer)
        workflow.add_node(NodeType.PLANNER, planner)
        workflow.add_node(NodeType.DISPATCHER, dispatcher)
        workflow.add_node(NodeType.LEGAL_RETRIEVER, legal_retriever)
        workflow.add_node(NodeType.DOC_RETRIEVER, doc_retriever)
        workflow.add_node(NodeType.HUMAN_REVIEWER, human_reviewer)
        workflow.add_node(NodeType.VERIFIER, verifier)
        workflow.add_node(NodeType.GENERATOR, generator)
        workflow.add_node(NodeType.EVALUATOR, evaluator)

        workflow.set_entry_point(NodeType.INITIALIZER)

        workflow.add_edge(NodeType.INITIALIZER, NodeType.PLANNER)
        workflow.add_edge(NodeType.PLANNER, NodeType.DISPATCHER)

        workflow.add_conditional_edges(
            NodeType.DISPATCHER,
            route_after_dispatcher,
            {
                NodeType.LEGAL_RETRIEVER: NodeType.LEGAL_RETRIEVER,
                NodeType.DOC_RETRIEVER: NodeType.DOC_RETRIEVER,
                NodeType.GENERATOR: NodeType.GENERATOR,
            },
        )

        workflow.add_edge(NodeType.LEGAL_RETRIEVER, NodeType.VERIFIER)
        workflow.add_edge(NodeType.DOC_RETRIEVER, NodeType.VERIFIER)

        workflow.add_conditional_edges(
            NodeType.VERIFIER,
            route_after_verifier,
            {
                NodeType.LEGAL_RETRIEVER: NodeType.LEGAL_RETRIEVER,
                NodeType.DOC_RETRIEVER: NodeType.DOC_RETRIEVER,
                NodeType.DISPATCHER: NodeType.DISPATCHER,
            },
        )

        workflow.add_edge(NodeType.GENERATOR, NodeType.EVALUATOR)

        workflow.add_conditional_edges(
            NodeType.EVALUATOR,
            route_after_evaluator,
            {
                NodeType.HUMAN_REVIEWER: NodeType.HUMAN_REVIEWER,
                NodeType.END_NODE: END,
            },
        )

        workflow.add_conditional_edges(
            NodeType.HUMAN_REVIEWER,
            route_after_human,
            {
                NodeType.PLANNER: NodeType.PLANNER,
                NodeType.GENERATOR: NodeType.GENERATOR,
                NodeType.END_NODE: END,
            },
        )

        return workflow
