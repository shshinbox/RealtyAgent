import os
from contextlib import asynccontextmanager
from typing import Dict

import aiosqlite
from fastapi import FastAPI
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from engine import GraphEngine
from engine.graph.schema import NodeType

from server.logger import logger
from server.api import api_router
from server.storage.redis_manager import RedisManager
from server.storage.postgresql_manager import PostgreSQLManager
from server.storage.qdrant_searcher import QdrantSearcher
from server.config import Settings
from ingestion.pipeline import DocumentPipeline
from ingestion.retriever import DocumentRetriever


def load_settings() -> Settings:
    app_env = os.getenv("APP_ENV")

    if app_env not in ("local", "docker"):
        raise ValueError("APP_ENV must be one of 'local', 'docker'.")

    env_files = ("server/.env", f"server/.env.{app_env}")

    class AppSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=env_files,
            env_file_encoding="utf-8",
            extra="ignore",
        )

    return AppSettings()


def build_llm_map(settings: Settings) -> Dict[NodeType, BaseChatModel]:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")

    def llm(model: str):
        return ChatOpenAI(
            model=model,
            api_key=SecretStr(settings.OPENAI_API_KEY or ""),
            temperature=0,
        )

    return {
        NodeType.PLANNER: llm("gpt-4o"),
        NodeType.GENERATOR: llm("gpt-4o-mini"),
        NodeType.DOC_RETRIEVER: llm("gpt-4o-mini"),
        NodeType.LEGAL_RETRIEVER: llm("gpt-4o-mini"),
        NodeType.HUMAN_REVIEWER: llm("gpt-4o-mini"),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):

    # ---- Settings ----
    settings = load_settings()
    app.state.settings = settings
    logger.info("Settings loaded")

    # ---- Storage ----
    redis_manager = RedisManager(settings.REDIS_URL or "")
    postgresql_manager = PostgreSQLManager(settings.POSTGRESQL_URL or "")
    qdrant_searcher = QdrantSearcher(
        host=settings.QDRANT_HOST or "",
        port=settings.QDRANT_PORT or -1,
    )

    # ---- Checkpointer ----
    sqlite_conn = await aiosqlite.connect("checkpoints.db")
    checkpointer = AsyncSqliteSaver(sqlite_conn)
    await checkpointer.setup()

    # ---- LLM ----
    llm_map = build_llm_map(settings)

    # ---- Engine ----
    engine = GraphEngine(
        llm_map=llm_map,
        checkpointer=checkpointer,
    )

    # ---- Ingestion ----
    neo4j_kwargs = dict(
        neo4j_url=settings.NEO4J_URL or "",
        neo4j_username=settings.NEO4J_USERNAME or "",
        neo4j_password=settings.NEO4J_PASSWORD or "",
    )
    pipeline = DocumentPipeline(
        qdrant_host=settings.QDRANT_HOST or "",
        qdrant_port=settings.QDRANT_PORT or -1,
        openai_api_key=settings.OPENAI_API_KEY or "",
        **neo4j_kwargs,
    )
    retriever = DocumentRetriever(
        qdrant_host=settings.QDRANT_HOST or "",
        qdrant_port=settings.QDRANT_PORT or -1,
        openai_api_key=settings.OPENAI_API_KEY or "",
        **neo4j_kwargs,
    )

    # ---- Inject ----
    app.state.settings = settings
    app.state.engine = engine
    app.state.redis = redis_manager
    app.state.pg = postgresql_manager
    app.state.qdrant = qdrant_searcher
    app.state.pipeline = pipeline
    app.state.retriever = retriever

    logger.info("System initialized")

    try:
        yield
    finally:
        logger.info("Shutting down...")

        await sqlite_conn.close()
        await redis_manager.close()
        await postgresql_manager.close()
        await qdrant_searcher.close()

        logger.info("Shutdown complete")


# =====================
# FastAPI App
# =====================
app = FastAPI(lifespan=lifespan)
app.include_router(router=api_router)


@app.get("/", response_model=dict)
async def root() -> dict:
    return {"message": "Gateway is running."}
