import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
from engine.graph.nodes.base import ToolNode, LLMNode
from engine.graph.state import StateManager, AgentState, StateKey
from engine.graph.schema import NodeType
from engine.graph.nodes.dispatcher import Dispatcher


@pytest.fixture
def dispatcher():
    return Dispatcher()


@patch("engine.graph.nodes.dispatcher.StateManager")
def test_dispatcher_routing(MockManager, dispatcher):
    # 1. Setup: 매니저와 플래너 모킹
    sm = MockManager.return_value
    planner = MagicMock()
    sm.planner_response = planner

    # Case 1: 스택이 비었을 때 -> GENERATOR로 가야 함
    planner.is_exhausted.return_value = True
    res1 = dispatcher({})
    assert res1[StateKey.NEXT_NODE] == NodeType.GENERATOR

    # Case 2: 스택에 값이 있을 때 -> pop_stack() 결과로 가야 함
    planner.is_exhausted.return_value = False
    planner.pop_stack.return_value = NodeType.LEGAL_RETRIEVER
    res2 = dispatcher({})
    assert res2[StateKey.NEXT_NODE] == NodeType.LEGAL_RETRIEVER

    # 검증: 에러 없고 플래너 객체 그대로 반환되는지
    assert res2[StateKey.ERRORS] is None
    assert res2[StateKey.PLANNER_RESPONSE] == planner
