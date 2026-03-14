from langgraph.graph import StateGraph
from langgraph.graph import StateGraph, END
from langchain_core.language_models import BaseChatModel

from .state import AgentState
from .router import (
    route_after_dispatcher,
    route_after_legal_retriever,
    route_after_doc_retriever,
    route_after_evaluator,
    route_after_counselor,
    route_after_human,
)
from .schema import NodeType
from .nodes.initialize import Initializer
from .nodes.legal_retriever import LegalRetriever
from .nodes.doc_retriever import DocumentsRetriever
from .nodes.memory_retriever import MemoryRetriever
from .nodes.dispatcher import Dispatcher
from .nodes.counselor import Counselor
from .nodes.human_reviewer import HumanReviewer
from .nodes.planner import Planner
from .nodes.generator import Generator
from .nodes.evaluator import Evaluator
from .nodes.finalizer import Finalizer


def build_workflow(llm_map: dict[NodeType, BaseChatModel]) -> StateGraph:
    workflow: StateGraph = StateGraph(AgentState)

    initializer: Initializer = Initializer()
    planner: Planner = Planner(llm=llm_map[NodeType.PLANNER])
    dispatcher: Dispatcher = Dispatcher()
    legal_retriever: LegalRetriever = LegalRetriever(
        llm=llm_map[NodeType.LEGAL_RETRIEVER]
    )
    doc_retriever: DocumentsRetriever = DocumentsRetriever()
    memory_retriever: MemoryRetriever = MemoryRetriever()
    counselor: Counselor = Counselor(llm=llm_map[NodeType.COUNSELOR])
    human_reviewer: HumanReviewer = HumanReviewer(llm=llm_map[NodeType.HUMAN_REVIEWER])
    generator: Generator = Generator(llm=llm_map[NodeType.GENERATOR])
    evaluator: Evaluator = Evaluator()
    finalizer: Finalizer = Finalizer()

    workflow.add_node(NodeType.INITIALIZER, initializer)
    workflow.add_node(NodeType.PLANNER, planner)
    workflow.add_node(NodeType.DISPATCHER, dispatcher)
    workflow.add_node(NodeType.COUNSELOR, counselor)
    workflow.add_node(NodeType.LEGAL_RETRIEVER, legal_retriever)
    workflow.add_node(NodeType.DOC_RETRIEVER, doc_retriever)
    workflow.add_node(NodeType.MEMORY_RETRIEVER, memory_retriever)
    workflow.add_node(NodeType.HUMAN_REVIEWER, human_reviewer)
    workflow.add_node(NodeType.GENERATOR, generator)
    workflow.add_node(NodeType.EVALUATOR, evaluator)
    workflow.add_node(NodeType.FINALIZER, finalizer)

    workflow.set_entry_point(NodeType.INITIALIZER)

    workflow.add_edge(NodeType.INITIALIZER, NodeType.PLANNER)
    workflow.add_edge(NodeType.PLANNER, NodeType.DISPATCHER)

    workflow.add_conditional_edges(
        NodeType.DISPATCHER,
        route_after_dispatcher,
        {
            NodeType.LEGAL_RETRIEVER: NodeType.LEGAL_RETRIEVER,
            NodeType.DOC_RETRIEVER: NodeType.DOC_RETRIEVER,
            NodeType.MEMORY_RETRIEVER: NodeType.MEMORY_RETRIEVER,
            NodeType.COUNSELOR: NodeType.COUNSELOR,
            NodeType.GENERATOR: NodeType.GENERATOR,
            NodeType.HUMAN_REVIEWER: NodeType.HUMAN_REVIEWER,
            NodeType.FINALIZER: NodeType.FINALIZER,
        },
    )

    workflow.add_conditional_edges(
        NodeType.COUNSELOR,
        route_after_counselor,
        {
            NodeType.COUNSELOR: NodeType.COUNSELOR,
            NodeType.DISPATCHER: NodeType.DISPATCHER,
        },
    )

    workflow.add_conditional_edges(
        NodeType.LEGAL_RETRIEVER,
        route_after_legal_retriever,
        {
            NodeType.LEGAL_RETRIEVER: NodeType.LEGAL_RETRIEVER,
            NodeType.DISPATCHER: NodeType.DISPATCHER,
        },
    )

    workflow.add_conditional_edges(
        NodeType.DOC_RETRIEVER,
        route_after_doc_retriever,
        {
            NodeType.DOC_RETRIEVER: NodeType.DOC_RETRIEVER,
            NodeType.DISPATCHER: NodeType.DISPATCHER,
        },
    )

    workflow.add_edge(NodeType.MEMORY_RETRIEVER, NodeType.DISPATCHER)

    workflow.add_edge(NodeType.GENERATOR, NodeType.EVALUATOR)

    workflow.add_conditional_edges(
        NodeType.EVALUATOR,
        route_after_evaluator,
        {
            NodeType.GENERATOR: NodeType.GENERATOR,
            NodeType.HUMAN_REVIEWER: NodeType.HUMAN_REVIEWER,
            NodeType.DISPATCHER: NodeType.DISPATCHER,
        },
    )

    workflow.add_conditional_edges(
        NodeType.HUMAN_REVIEWER,
        route_after_human,
        {
            NodeType.PLANNER: NodeType.PLANNER,
            NodeType.GENERATOR: NodeType.GENERATOR,
            NodeType.DISPATCHER: NodeType.DISPATCHER,
        },
    )

    workflow.add_edge(NodeType.FINALIZER, END)

    return workflow
