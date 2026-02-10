from typing import List, Dict, Any, Optional
from qdrant_client.conversions import common_types as types
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams,
    ScoredPoint,
)
import asyncio


class QdrantSearcher:
    def __init__(
        self,
        host: str,
        port: int,
    ):
        if not host or not port or port <= 0:
            raise ValueError("host and port are required")

        self.client = AsyncQdrantClient(
            host=host,
            port=port,
        )

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ):
        """
        컬렉션 생성

        Args:
            collection_name: 컬렉션 이름
            vector_size: 벡터 차원
            distance: 거리 측정 방법 (COSINE, EUCLID, DOT)
        """
        await self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )
        print(f"컬렉션 '{collection_name}' 생성 완료")

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

        await self.client.upsert(collection_name=collection_name, points=points)
        print(f"{len(documents)}개 문서 삽입 완료")

    async def search_similar_docs(
        self,
        query_vector: list[float],
        collection_name: str,
        top_k: int = 5,
        filter: Filter | None = None,
        with_payload: bool = True,
    ):
        """
        qdrant_client.query_points를 사용한 유사도 검색 함수
        """

        response: types.QueryResponse = await self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=filter,
            with_payload=with_payload,
            with_vectors=False,  # 벡터 필요없으면 False
        )

        results = []
        for point in response.points:
            results.append(
                {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload,
                }
            )

        return results

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
                collection_name=collection_name, query_vector=query_vector, top_k=limit
            )
            for query_vector in query_vectors
        ]

        results = await asyncio.gather(*tasks)
        return results

    async def close(self):
        await self.client.close()
