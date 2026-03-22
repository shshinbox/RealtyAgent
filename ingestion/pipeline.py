import asyncio
import shutil
import tempfile
from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.graph_stores.types import KG_NODES_KEY, KG_RELATIONS_KEY
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from qdrant_client import AsyncQdrantClient

from .extractors.llm_extractor import build_llm_extractor
from .extractors.rule_extractor import RealtyRuleExtractor


class DocumentPipeline:
    COLLECTION_NAME = "documents"

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        graph_store: Neo4jPropertyGraphStore,
        llm: LLM,
        embed_model: BaseEmbedding,
    ):
        self._qdrant_client = qdrant_client
        self._graph_store = graph_store
        self._embed_model = embed_model
        self._splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        self._kg_extractors = [
            build_llm_extractor(llm=llm),
            RealtyRuleExtractor(),
        ]

    async def ingest(self, file_bytes: bytes, filename: str, metadata: dict = {}) -> int:
        return await self._ingest_async(file_bytes, filename, metadata)

    async def ingest_directory(self, directory: str, metadata: dict = {}) -> dict:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise ValueError(f"디렉토리가 존재하지 않습니다: {directory}")

        pdf_files = list(dir_path.glob("**/*.pdf"))
        if not pdf_files:
            return {"total_files": 0, "total_chunks": 0, "files": []}

        results = []
        total_chunks = 0
        for pdf_path in pdf_files:
            try:
                chunks = await self._ingest_async(
                    file_bytes=pdf_path.read_bytes(),
                    filename=pdf_path.name,
                    metadata={**metadata, "filename": pdf_path.name, "source_path": str(pdf_path)},
                )
                results.append({"filename": pdf_path.name, "chunks": chunks, "status": "ok"})
                total_chunks += chunks
            except Exception as e:
                results.append({"filename": pdf_path.name, "chunks": 0, "status": f"error: {e}"})

        return {"total_files": len(pdf_files), "total_chunks": total_chunks, "files": results}

    async def _ingest_async(self, file_bytes: bytes, filename: str, metadata: dict) -> int:
        tmp_dir = tempfile.mkdtemp()
        try:
            file_path = Path(tmp_dir) / filename
            file_path.write_bytes(file_bytes)

            # 1. Load and chunk (sync, fast — OK inline)
            documents = SimpleDirectoryReader(input_files=[str(file_path)]).load_data()
            for doc in documents:
                doc.metadata.update(metadata)
            nodes = self._splitter.get_nodes_from_documents(documents)

            # 2. Apply KG extractors in thread (sync LLM API calls internally)
            for extractor in self._kg_extractors:
                nodes = await asyncio.to_thread(extractor, nodes)

            # 3. Write graph data to Neo4j in thread (sync driver)
            kg_nodes, kg_relations = [], []
            for node in nodes:
                kg_nodes.extend(node.metadata.get(KG_NODES_KEY, []))
                kg_relations.extend(node.metadata.get(KG_RELATIONS_KEY, []))

            if kg_nodes:
                await asyncio.to_thread(self._graph_store.upsert_nodes, kg_nodes)
            if kg_relations:
                await asyncio.to_thread(self._graph_store.upsert_relations, kg_relations)

            # 4. Embed source nodes (async OpenAI API)
            embeddings = await self._embed_model.aget_text_embedding_batch(
                [node.get_content() for node in nodes], show_progress=False
            )
            for node, embedding in zip(nodes, embeddings):
                node.embedding = embedding

            # 5. Write to Qdrant via async client
            vector_store = QdrantVectorStore(
                aclient=self._qdrant_client,
                collection_name=self.COLLECTION_NAME,
            )
            await vector_store.async_add(nodes)

            return len(nodes)
        finally:
            shutil.rmtree(tmp_dir)
