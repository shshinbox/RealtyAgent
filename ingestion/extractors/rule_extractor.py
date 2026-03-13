import re
from typing import Any, List

from llama_index.core.graph_stores.types import EntityNode, Relation, KG_NODES_KEY, KG_RELATIONS_KEY
from llama_index.core.schema import BaseNode, TransformComponent


# 부동산 도메인 법령명 패턴
LAW_PATTERN = re.compile(
    r"(주택법|건축법|공인중개사법|부동산거래신고법|민법|상가건물임대차보호법"
    r"|주택임대차보호법|집합건물법|도시정비법|국토계획법)"
    r"(?:\s*제\s*(\d+)조)?"
)

# 면적 패턴 (평, ㎡)
AREA_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(평|㎡|m²)")

# 가격 패턴 (억, 만원)
PRICE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(억|만\s*원|원)")

# 행정구역 사전
REGIONS = [
    "강남구", "서초구", "송파구", "강동구", "마포구", "용산구", "종로구",
    "중구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구",
    "도봉구", "노원구", "은평구", "서대문구", "양천구", "강서구", "구로구",
    "금천구", "영등포구", "동작구", "관악구", "서울특별시", "경기도", "인천광역시",
    "부산광역시", "대구광역시", "광주광역시", "대전광역시", "울산광역시",
]
REGION_PATTERN = re.compile("|".join(re.escape(r) for r in REGIONS))

# 건물 유형 사전
PROPERTY_TYPES = ["아파트", "오피스텔", "빌라", "단독주택", "상가", "오피스", "토지"]
PROPERTY_PATTERN = re.compile("|".join(re.escape(t) for t in PROPERTY_TYPES))


class RealtyRuleExtractor(TransformComponent):
    """
    부동산 도메인 규칙 기반 개체/관계 추출기.
    정규식과 키워드 사전으로 법령명, 지역명, 면적, 가격, 건물 유형을 추출합니다.

    LLM 추출기가 놓치기 쉬운 수치 정보와 패턴이 명확한 도메인 개체를 보완합니다.
    """

    def __call__(self, nodes: List[BaseNode], **kwargs: Any) -> List[BaseNode]:
        for node in nodes:
            text = node.get_content()
            existing_nodes: list = node.metadata.get(KG_NODES_KEY, [])
            existing_relations: list = node.metadata.get(KG_RELATIONS_KEY, [])

            new_nodes, new_relations = self._extract(text)

            node.metadata[KG_NODES_KEY] = existing_nodes + new_nodes
            node.metadata[KG_RELATIONS_KEY] = existing_relations + new_relations

        return nodes

    def _extract(self, text: str) -> tuple[list, list]:
        entity_nodes = []
        relations = []

        # 법령명 추출
        for match in LAW_PATTERN.finditer(text):
            law_name = match.group(0).strip()
            law_node = EntityNode(name=law_name, label="법령")
            entity_nodes.append(law_node)

        # 지역명 추출
        region_nodes = {}
        for match in REGION_PATTERN.finditer(text):
            region = match.group(0)
            if region not in region_nodes:
                region_node = EntityNode(name=region, label="지역")
                entity_nodes.append(region_node)
                region_nodes[region] = region_node

        # 건물 유형 추출 + 지역과 관계 연결
        for match in PROPERTY_PATTERN.finditer(text):
            prop_type = match.group(0)
            prop_node = EntityNode(name=prop_type, label="건물유형")
            entity_nodes.append(prop_node)

            # 근처 지역명이 있으면 관계 생성
            start = max(0, match.start() - 30)
            context = text[start: match.end()]
            for region, region_node in region_nodes.items():
                if region in context:
                    relations.append(
                        Relation(
                            label="위치",
                            source_id=prop_node.id,
                            target_id=region_node.id,
                        )
                    )

        # 면적 추출
        for match in AREA_PATTERN.finditer(text):
            value, unit = match.group(1), match.group(2)
            area_node = EntityNode(name=f"{value}{unit}", label="면적")
            entity_nodes.append(area_node)

        # 가격 추출
        for match in PRICE_PATTERN.finditer(text):
            value, unit = match.group(1), match.group(2).replace(" ", "")
            price_node = EntityNode(name=f"{value}{unit}", label="가격")
            entity_nodes.append(price_node)

        return entity_nodes, relations
