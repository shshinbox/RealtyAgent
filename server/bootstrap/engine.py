from dataclasses import dataclass
from typing import Dict

import aiosqlite
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from engine import GraphEngine
from engine.graph.schema import NodeType


@dataclass
class EngineBundle:
    engine: GraphEngine
    sqlite_conn: aiosqlite.Connection


async def build_engine(llm_map: Dict[NodeType, BaseChatModel]) -> EngineBundle:
    sqlite_conn = await aiosqlite.connect("checkpoints.db")
    checkpointer = AsyncSqliteSaver(sqlite_conn)
    await checkpointer.setup()

    engine = GraphEngine(llm_map=llm_map, checkpointer=checkpointer)
    return EngineBundle(engine=engine, sqlite_conn=sqlite_conn)


async def close_engine(bundle: EngineBundle) -> None:
    await bundle.sqlite_conn.close()
