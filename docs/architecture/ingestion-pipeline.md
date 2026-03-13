# 문서 수집 파이프라인 (ingestion/)

## 개요

본 문서는 공문서(PDF)를 수집하여 검색 가능한 형태로 저장하는
파이프라인의 설계 및 구현을 정의합니다.

구현은 `ingestion/` 패키지로 분리하며, **LlamaIndex** 프레임워크를 활용합니다.
`engine/`(LangGraph)과는 `ExternalDepsPort` 인터페이스를 통해서만 연결되므로
프레임워크 간 직접적인 의존성은 발생하지 않습니다.

---

## 패키지 구조

```
ingestion/
  ├── __init__.py
  ├── pipeline.py              # 문서 수집 및 저장 (PDF → Qdrant + Neo4j)
  ├── retriever.py             # 하이브리드 검색 (Vector + Graph)
  └── extractors/
        ├── __init__.py
        ├── llm_extractor.py   # LLM 기반 개체/관계 추출
        └── rule_extractor.py  # 규칙 기반 개체/관계 추출 (부동산 도메인 특화)
```

`server/service/external_deps_service.py`의 `search_docs()`가
`ingestion/retriever.py`를 호출하는 방식으로 연결됩니다.

---

## 수집 파이프라인 흐름

```
PDF 파일 업로드 (API) 또는 디렉토리 스캔
  ↓
① 문서 로딩       SimpleDirectoryReader (LlamaIndex)
  ↓
② 청킹            SentenceSplitter (chunk_size=512, chunk_overlap=50)
  ↓
③ 개체/관계 추출  LLM 추출기 + 규칙 추출기 (병렬 실행)
  ↓
④-A Qdrant 저장   [collection: documents] 벡터 임베딩 저장
④-B Neo4j 저장    추출된 개체/관계를 그래프로 저장
```

---

## 개체/관계 추출기

두 추출기는 `PropertyGraphIndex`의 `kg_extractors` 파라미터로 동시에 주입되며,
각 추출 결과가 합산되어 Neo4j에 저장됩니다.

### LLM 추출기 (`llm_extractor.py`)

`SimpleLLMPathExtractor` 기반. LLM이 텍스트 문맥을 이해하여
자유로운 형태의 (주체, 관계, 대상) 트리플을 추출합니다.

| 항목 | 내용 |
|---|---|
| 모델 | `gpt-4o-mini` |
| 추출 단위 | 청크당 최대 10개 경로 |
| 강점 | 복잡한 문맥, 예상치 못한 관계 파악 |
| 약점 | API 비용 발생, 가끔 환각 가능성 |

추출 예시:
```
(은마아파트, 위치, 강남구 대치동)
(주택법 제49조, 규정, 분양가 상한제)
(강남구, 포함, 서울특별시)
```

### 규칙 추출기 (`rule_extractor.py`)

`TransformComponent` 직접 구현. 정규식과 키워드 사전으로
부동산 도메인 특화 개체를 추출합니다.

| 추출 대상 | 방식 | 예시 |
|---|---|---|
| 법령명 | 정규식 | `주택법`, `건축법 제5조` |
| 지역명 | 키워드 사전 (25개 구 + 광역시/도) | `강남구`, `서울특별시` |
| 건물 유형 | 키워드 사전 | `아파트`, `오피스텔` |
| 면적 | 정규식 | `30평`, `99㎡` |
| 가격 | 정규식 | `10억`, `5만원` |

건물 유형과 인근 지역명이 동시에 발견되면 **위치** 관계를 자동 생성합니다.

| 항목 | 내용 |
|---|---|
| 강점 | 정확도 높음, API 비용 없음 |
| 약점 | 사전에 정의된 패턴만 인식 |

---

## 검색 전략: 하이브리드

### 검색기 구성 (`retriever.py`)

| 검색기 | 저장소 | 역할 |
|---|---|---|
| `VectorContextRetriever` | Qdrant | 질문과 의미적으로 유사한 청크 검색 |
| `LLMSynonymRetriever` | Neo4j | 동의어/관련 개체 경로 그래프 탐색 |

### 하이브리드 검색 흐름

```
쿼리 입력
  ├─ VectorContextRetriever (Qdrant) → 유사 청크 Top-K
  └─ LLMSynonymRetriever (Neo4j)    → 관련 개체 및 관계 경로
          ↓
      결과 병합 (PropertyGraphIndex.as_retriever)
          ↓
    최종 컨텍스트 반환 → engine/DocRetriever
```

---

## 문서 업로드 API

| 엔드포인트 | 방식 | 설명 |
|---|---|---|
| `POST /documents/upload` | 단건 업로드 | PDF 파일 1개 |
| `POST /documents/upload/batch` | 다건 업로드 | 여러 파일 병렬 처리 (`asyncio.gather`) |
| `POST /documents/scan` | 서버 디렉토리 스캔 | `DOCS_DIR` 환경변수 경로의 PDF 전체 처리 |

---

## engine/과의 연결 구조

```
engine/graph/nodes/doc_retriever.py
  └─ ExternalDepsPort.search_docs()              ← 인터페이스 호출
       ↑
server/service/external_deps_service.py
  └─ search_docs()
       └─ ingestion/retriever.py (DocumentRetriever.search())
            ├─ VectorContextRetriever → Qdrant
            └─ LLMSynonymRetriever   → Neo4j
```

`engine/`은 LlamaIndex를 전혀 알지 못합니다.
검색 전략 변경이 `engine/` 코드에 영향을 주지 않습니다.

---

## 프레임워크 선택 근거: LlamaIndex

| 항목 | 내용 |
|---|---|
| PDF 로딩 | `SimpleDirectoryReader` 내장 지원 |
| 청킹 | `SentenceSplitter` 등 다양한 전략 |
| Qdrant 연동 | `QdrantVectorStore` 공식 지원 |
| Neo4j 연동 | `Neo4jPropertyGraphStore` 공식 지원 |
| GraphRAG | `PropertyGraphIndex` 성숙한 구현체 |
| 하이브리드 검색 | `VectorContextRetriever` + `LLMSynonymRetriever` 내장 |

기존 `engine/`은 LangChain 기반이나, `ingestion/`은 LlamaIndex로 독립 구성합니다.
두 프레임워크는 `ExternalDepsPort` 인터페이스를 경계로 분리되어 충돌하지 않습니다.

---

## 구현 단계

| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | PDF → 청킹 → Qdrant 저장 파이프라인 | ✅ 완료 |
| 2 | Neo4j 연동 및 PropertyGraphIndex 적용 | ✅ 완료 |
| 3 | LLM 추출기 (`llm_extractor.py`) | ✅ 완료 |
| 4 | 규칙 추출기 (`rule_extractor.py`) | ✅ 완료 |
| 5 | 하이브리드 검색 (`retriever.py`) | ✅ 완료 |
| 6 | 문서 업로드 API 엔드포인트 (단건/다건/스캔) | ✅ 완료 |
| 7 | `search_docs()` → 하이브리드 검색 연결 | ✅ 완료 |
