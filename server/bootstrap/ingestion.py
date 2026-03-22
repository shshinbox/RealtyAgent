from dataclasses import dataclass

from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

from server.config import Settings
from server.storage.qdrant_searcher import QdrantSearcher
from ingestion.pipeline import DocumentPipeline
from ingestion.retriever import DocumentRetriever


@dataclass
class IngestionBundle:
    pipeline: DocumentPipeline
    retriever: DocumentRetriever


def build_ingestion(
    settings: Settings,
    qdrant_searcher: QdrantSearcher,
    graph_store: Neo4jPropertyGraphStore,
) -> IngestionBundle:
    openai_api_key: str = settings.OPENAI_API_KEY or ""
    llm = OpenAI(model="gpt-5.4-mini", api_key=openai_api_key)
    embed_model = OpenAIEmbedding(model="text-embedding-3-small", api_key=openai_api_key)

    return IngestionBundle(
        pipeline=DocumentPipeline(
            qdrant_client=qdrant_searcher,
            graph_store=graph_store,
            llm=llm,
            embed_model=embed_model,
        ),
        retriever=DocumentRetriever(
            qdrant_client=qdrant_searcher,
            graph_store=graph_store,
            llm=llm,
            embed_model=embed_model,
        ),
    )
