from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server.logger import logger
from server.api import api_router
from server.bootstrap.settings import load_settings
from server.bootstrap.llm import build_llm_map
from server.bootstrap.storage import build_storage, close_storage
from server.bootstrap.engine import build_engine, close_engine
from server.bootstrap.ingestion import build_ingestion


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    logger.info("Settings loaded")

    storage = build_storage(settings)
    engine_bundle = await build_engine(build_llm_map(settings))
    ingestion = build_ingestion(settings, storage.qdrant, storage.neo4j)

    app.state.settings = settings
    app.state.engine = engine_bundle.engine
    app.state.redis = storage.redis
    app.state.pg = storage.pg
    app.state.qdrant = storage.qdrant
    app.state.pipeline = ingestion.pipeline
    app.state.retriever = ingestion.retriever

    logger.info("System initialized")

    try:
        yield
    finally:
        logger.info("Shutting down...")
        await close_engine(engine_bundle)
        await close_storage(storage)
        logger.info("Shutdown complete")


app = FastAPI(lifespan=lifespan)
app.include_router(router=api_router)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
