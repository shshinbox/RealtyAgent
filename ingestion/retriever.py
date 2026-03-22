from llama_index.core import PropertyGraphIndex
from llama_index.core.indices.property_graph import (
    VectorContextRetriever,
    LLMSynonymRetriever,
)
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient


class DocumentRetriever:
    """
    하이브리드 검색기 (Vector + Graph).

    - VectorContextRetriever : Qdrant 유사도 검색으로 관련 청크 반환
    - LLMSynonymRetriever    : Neo4j 그래프에서 동의어/관련 개체 경로 탐색
    두 결과를 합산하여 반환합니다.
    """

    COLLECTION_NAME = "documents"

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        graph_store: Neo4jPropertyGraphStore,
        llm: LLM,
        embed_model: BaseEmbedding,
    ):
        vector_store = QdrantVectorStore(
            aclient=qdrant_client,
            collection_name=self.COLLECTION_NAME,
        )

        index = PropertyGraphIndex.from_existing(
            property_graph_store=graph_store,
            vector_store=vector_store,
            embed_model=embed_model,
            llm=llm,
        )

        self._retriever = index.as_retriever(
            sub_retrievers=[
                VectorContextRetriever(
                    graph_store=graph_store,
                    vector_store=vector_store,
                    embed_model=embed_model,
                    similarity_top_k=5,
                ),
                LLMSynonymRetriever(
                    graph_store=graph_store,
                    llm=llm,
                    synonym_expand_fn=None,
                ),
            ]
        )

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        nodes = await self._retriever.aretrieve(query)
        return [
            {
                "text": node.get_content(),
                "score": node.score,
                "metadata": node.metadata,
            }
            for node in nodes[:top_k]
        ]
