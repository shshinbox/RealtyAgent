import asyncio
import shutil
import tempfile
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, StorageContext, PropertyGraphIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from qdrant_client import QdrantClient

from .extractors.llm_extractor import build_llm_extractor
from .extractors.rule_extractor import RealtyRuleExtractor


class DocumentPipeline:
    COLLECTION_NAME = "documents"
    EMBED_MODEL = "text-embedding-3-small"

    def __init__(
        self,
        qdrant_host: str,
        qdrant_port: int,
        openai_api_key: str,
        neo4j_url: str,
        neo4j_username: str,
        neo4j_password: str,
    ):
        self._qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self._embed_model = OpenAIEmbedding(
            model=self.EMBED_MODEL,
            api_key=openai_api_key,
        )
        self._splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        self._graph_store = Neo4jPropertyGraphStore(
            username=neo4j_username,
            password=neo4j_password,
            url=neo4j_url,
        )
        self._kg_extractors = [
            build_llm_extractor(openai_api_key=openai_api_key),
            RealtyRuleExtractor(),
        ]

    async def ingest(
        self, file_bytes: bytes, filename: str, metadata: dict = {}
    ) -> int:
        return await asyncio.to_thread(
            self._ingest_sync, file_bytes, filename, metadata
        )

    async def ingest_directory(self, directory: str, metadata: dict = {}) -> dict:
        return await asyncio.to_thread(self._ingest_directory_sync, directory, metadata)

    def _ingest_directory_sync(self, directory: str, metadata: dict) -> dict:
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
                chunks = self._ingest_sync(
                    file_bytes=pdf_path.read_bytes(),
                    filename=pdf_path.name,
                    metadata={**metadata, "filename": pdf_path.name, "source_path": str(pdf_path)},
                )
                results.append({"filename": pdf_path.name, "chunks": chunks, "status": "ok"})
                total_chunks += chunks
            except Exception as e:
                results.append({"filename": pdf_path.name, "chunks": 0, "status": f"error: {e}"})

        return {"total_files": len(pdf_files), "total_chunks": total_chunks, "files": results}

    def _ingest_sync(self, file_bytes: bytes, filename: str, metadata: dict) -> int:
        tmp_dir = tempfile.mkdtemp()
        try:
            file_path = Path(tmp_dir) / filename
            file_path.write_bytes(file_bytes)

            documents = SimpleDirectoryReader(input_files=[str(file_path)]).load_data()
            for doc in documents:
                doc.metadata.update(metadata)

            nodes = self._splitter.get_nodes_from_documents(documents)

            vector_store = QdrantVectorStore(
                client=self._qdrant_client,
                collection_name=self.COLLECTION_NAME,
            )
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                property_graph_store=self._graph_store,
            )

            PropertyGraphIndex(
                nodes=nodes,
                storage_context=storage_context,
                embed_model=self._embed_model,
                kg_extractors=self._kg_extractors,
                show_progress=False,
            )

            return len(nodes)
        finally:
            shutil.rmtree(tmp_dir)
