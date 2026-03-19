from dataclasses import dataclass

from server.config import Settings
from ingestion.pipeline import DocumentPipeline
from ingestion.retriever import DocumentRetriever


@dataclass
class IngestionBundle:
    pipeline: DocumentPipeline
    retriever: DocumentRetriever


def build_ingestion(settings: Settings) -> IngestionBundle:
    qdrant_host: str = settings.QDRANT_HOST or ""
    qdrant_port: int = int(settings.QDRANT_PORT or -1)
    openai_api_key: str = settings.OPENAI_API_KEY or ""
    neo4j_url: str = settings.NEO4J_URL or ""
    neo4j_username: str = settings.NEO4J_USERNAME or ""
    neo4j_password: str = settings.NEO4J_PASSWORD or ""

    return IngestionBundle(
        pipeline=DocumentPipeline(
            qdrant_host=qdrant_host,
            qdrant_port=qdrant_port,
            openai_api_key=openai_api_key,
            neo4j_url=neo4j_url,
            neo4j_username=neo4j_username,
            neo4j_password=neo4j_password,
        ),
        retriever=DocumentRetriever(
            qdrant_host=qdrant_host,
            qdrant_port=qdrant_port,
            openai_api_key=openai_api_key,
            neo4j_url=neo4j_url,
            neo4j_username=neo4j_username,
            neo4j_password=neo4j_password,
        ),
    )
