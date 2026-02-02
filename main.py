from fastapi import FastAPI
from contextlib import asynccontextmanager
import aiosqlite
from pydantic import SecretStr

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from engine import GraphEngine

from engine.graph.schema import NodeType
from server.logger import logger
from server.api import api_router
from server.config import settings
from server.storage.redis_client import redis_client
from server.storage.postgresql_client import postgresql_engine
from server.storage.qdrant_client import qdrant_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

    llm_map: dict[NodeType, BaseChatModel] = {
        NodeType.PLANNER: ChatOpenAI(
            model="gpt-4o",
            api_key=SecretStr(settings.OPENAI_API_KEY),
            temperature=0,
        ),
        NodeType.GENERATOR: ChatOpenAI(
            model="gpt-4o-mini",
            api_key=SecretStr(settings.OPENAI_API_KEY),
            temperature=0,
        ),
        NodeType.DOC_RETRIEVER: ChatOpenAI(
            model="gpt-4o-mini",
            api_key=SecretStr(settings.OPENAI_API_KEY),
            temperature=0,
        ),
        NodeType.LEGAL_RETRIEVER: ChatOpenAI(
            model="gpt-4o-mini",
            api_key=SecretStr(settings.OPENAI_API_KEY),
            temperature=0,
        ),
        NodeType.HUMAN_REVIEWER: ChatOpenAI(
            model="gpt-4o-mini",
            api_key=SecretStr(settings.OPENAI_API_KEY),
            temperature=0,
        ),
    }

    sqlite_conn = await aiosqlite.connect("checkpoints.db")
    checkpointer = AsyncSqliteSaver(sqlite_conn)
    await checkpointer.setup()

    app.state.postgresql = postgresql_engine
    app.state.redis_client = redis_client
    app.state.qdrant_client = qdrant_client

    app.state.engine = GraphEngine(llm_map=llm_map, checkpointer=checkpointer)

    logger.info("AI Graph Engine Initialized.")

    try:
        yield
    finally:
        logger.info("Shutting down resources...")

        await sqlite_conn.close()
        await postgresql_engine.dispose()
        await redis_client.close()
        await qdrant_client.close()

        logger.info("All resources safely closed.")


app = FastAPI(lifespan=lifespan)

app.include_router(router=api_router)


@app.get("/", response_model=dict)
async def root() -> dict:
    return {"message": "Gateway is running."}
