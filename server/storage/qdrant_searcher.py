import asyncio
from typing import List, Dict, Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.conversions import common_types as types
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)


class QdrantSearcher(AsyncQdrantClient):
    def __init__(self, host: str, port: int):
        if not host or not port or port <= 0:
            raise ValueError("host and port are required")
        super().__init__(host=host, port=port)

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        **kwargs,
    ):
        """
        컬렉션 생성

        Args:
            collection_name: 컬렉션 이름
            vector_size: 벡터 차원
            distance: 거리 측정 방법 (COSINE, EUCLID, DOT)
        """
        await super().create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )

    async def insert_documents(
        self, collection_name: str, documents: List[Dict[str, Any]]
    ):
        """
        문서 삽입

        Args:
            collection_name: 컬렉션 이름
            documents: 문서 리스트 (각 문서는 id, vector, payload 포함)
                      예: [{"id": 1, "vector": [...], "payload": {"text": "..."}}]
        """
        points = [
            PointStruct(
                id=doc["id"], vector=doc["vector"], payload=doc.get("payload", {})
            )
            for doc in documents
        ]
        await self.upsert(collection_name=collection_name, points=points)

    async def search_similar_docs(
        self,
        query_vector: list[float],
        collection_name: str,
        top_k: int = 5,
        filter: Filter | None = None,
        with_payload: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        qdrant_client.query_points를 사용한 유사도 검색 함수
        """
        response: types.QueryResponse = await self.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=filter,
            with_payload=with_payload,
            with_vectors=False,
        )
        return [
            {"id": point.id, "score": point.score, "payload": point.payload}
            for point in response.points
        ]

    async def search_with_metadata_filter(
        self,
        collection_name: str,
        query_vector: List[float],
        metadata_fields: List[str],
        metadata_values: List[Any],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        메타데이터 필터링과 함께 검색

        Args:
            collection_name: 컬렉션 이름
            query_vector: 검색 쿼리 벡터
            metadata_field: 필터링할 메타데이터 필드명
            metadata_value: 필터링할 값
            limit: 반환할 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key=metadata_fields[i], match=MatchValue(value=metadata_values[i])
                )
                for i in range(len(metadata_fields))
            ]
        )
        return await self.search_similar_docs(
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=limit,
            filter=filter_condition,
        )

    async def batch_search(
        self, collection_name: str, query_vectors: List[List[float]], limit: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """
        배치 검색 (여러 쿼리 동시 처리)

        Args:
            collection_name: 컬렉션 이름
            query_vectors: 검색 쿼리 벡터 리스트
            limit: 각 쿼리당 반환할 최대 결과 수

        Returns:
            각 쿼리에 대한 검색 결과 리스트
        """
        tasks = [
            self.search_similar_docs(
                collection_name=collection_name, query_vector=qv, top_k=limit
            )
            for qv in query_vectors
        ]
        return await asyncio.gather(*tasks)
