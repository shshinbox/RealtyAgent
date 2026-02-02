from langgraph.graph import StateGraph
from langgraph.graph import StateGraph, END
from langchain_core.language_models import BaseChatModel

from .state import AgentState, StateKey
from .router import (
    route_after_dispatcher,
    route_after_verifier,
    route_after_evaluator,
    route_after_human,
)
from .schema import NodeType
from .nodes.initialize import Initializer
from .nodes.legal_retriever import LegalRetriever
from .nodes.doc_retriever import DocumentsRetriever
from .nodes.dispatcher import Dispatcher
from .nodes.human_reviewer import HumanReviewer
from .nodes.planner import Planner
from .nodes.verifier import Verifier
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
    doc_retriever: DocumentsRetriever = DocumentsRetriever(
        llm=llm_map[NodeType.DOC_RETRIEVER]
    )
    human_reviewer: HumanReviewer = HumanReviewer(llm=llm_map[NodeType.HUMAN_REVIEWER])
    verifier: Verifier = Verifier()
    generator: Generator = Generator(llm=llm_map[NodeType.GENERATOR])
    evaluator: Evaluator = Evaluator()
    finalizer: Finalizer = Finalizer()

    workflow.add_node(NodeType.INITIALIZER, initializer)
    workflow.add_node(NodeType.PLANNER, planner)
    workflow.add_node(NodeType.DISPATCHER, dispatcher)
    workflow.add_node(NodeType.LEGAL_RETRIEVER, legal_retriever)
    workflow.add_node(NodeType.DOC_RETRIEVER, doc_retriever)
    workflow.add_node(NodeType.HUMAN_REVIEWER, human_reviewer)
    workflow.add_node(NodeType.VERIFIER, verifier)
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
            NodeType.GENERATOR: NodeType.GENERATOR,
            NodeType.HUMAN_REVIEWER: NodeType.HUMAN_REVIEWER,
            NodeType.FINALIZER: NodeType.FINALIZER,
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
