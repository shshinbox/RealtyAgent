import os
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    KnowledgeGraphIndex,
    StorageContext,
)
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from dotenv import load_dotenv


# ── 1. LLM / Embedding 설정 ──────────────────────────────────────────────────
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
Settings.llm = OpenAI(model="gpt-4o", temperature=0, api_key=api_key)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small", api_key=api_key)


# ── 2. 샘플 문서 (파일 없이 인라인으로 테스트) ───────────────────────────────
from llama_index.core import Document

documents = [
    Document(
        text="아이언맨(토니 스타크)은 마블 유니버스의 영웅으로 어벤져스를 이끌었다."
    ),
    Document(text="캡틴 아메리카(스티브 로저스)는 어벤져스의 창립 멤버이다."),
    Document(text="토르는 아스가르드의 신이며 어벤져스와 함께 타노스와 싸웠다."),
    Document(text="타노스는 인피니티 건틀렛을 이용해 우주의 절반을 없애려 했다."),
    Document(
        text="어벤져스는 아이언맨, 캡틴 아메리카, 토르, 헐크, 블랙 위도우로 구성된다."
    ),
]

# ── 3. 인메모리 Graph Store 생성 ─────────────────────────────────────────────
graph_store = SimpleGraphStore()
storage_context = StorageContext.from_defaults(graph_store=graph_store)

# ── 4. KnowledgeGraphIndex 구축 ──────────────────────────────────────────────
#   - max_triplets_per_chunk: 청크당 추출할 (주어, 관계, 목적어) 트리플 최대 수
#   - include_embeddings: 벡터 유사도 검색도 함께 활용
print("📊 Knowledge Graph 구축 중...")
index = KnowledgeGraphIndex.from_documents(
    documents,
    storage_context=storage_context,
    max_triplets_per_chunk=5,
    include_embeddings=True,
    show_progress=True,
)

# ── 5. 그래프에서 추출된 트리플 확인 ────────────────────────────────────────
print("\n🔗 추출된 Knowledge Graph 트리플:")
for subj, rel_obj_list in graph_store._data.graph_dict.items():
    for rel, obj in rel_obj_list:
        print(f"  ({subj}) --[{rel}]--> ({obj})")

# ── 6. Query Engine 생성 및 질의 ─────────────────────────────────────────────
#   retriever_mode 옵션:
#     "keyword"   : 키워드 기반 그래프 탐색
#     "embedding" : 벡터 유사도 기반 탐색
#     "hybrid"    : 두 방식 결합 (권장)
query_engine = index.as_query_engine(
    retriever_mode="hybrid",
    verbose=True,  # 어떤 노드/관계를 참조했는지 출력
    response_mode="tree_summarize",
)

# ── 7. 질문 & 답변 ───────────────────────────────────────────────────────────
questions = [
    "어벤져스의 멤버는 누구인가요?",
    "타노스가 사용한 무기는 무엇인가요?",
    "아이언맨의 본명은 무엇인가요?",
]

print("\n" + "=" * 60)
for q in questions:
    print(f"\n❓ 질문: {q}")
    response = query_engine.query(q)
    print(f"💬 답변: {response}\n")
    print("-" * 60)

# ── 8. (선택) 그래프 시각화 ──────────────────────────────────────────────────
try:
    from pyvis.network import Network

    net = Network(height="600px", width="100%", notebook=False)
    for subj, rel_obj_list in graph_store._data.graph_dict.items():
        net.add_node(subj, label=subj, color="#4a90e2")
        for rel, obj in rel_obj_list:
            net.add_node(obj, label=obj, color="#7ed321")
            net.add_edge(subj, obj, label=rel)
    net.save_graph("sample/graph_rag_visualization.html")
    print("✅ 그래프 시각화 저장됨: graph_rag_visualization.html")
except ImportError:
    print("💡 시각화를 원하면: pip install pyvis")

# ── 9. (선택) Neo4j 영구 저장소로 교체하는 방법 ──────────────────────────────
"""
from llama_index.graph_stores.neo4j import Neo4jGraphStore

graph_store = Neo4jGraphStore(
    username=os.environ["NEO4J_USER"],
    password=os.environ["NEO4J_PASSWORD"],
    url=os.environ["NEO4J_URI"],           # bolt://localhost:7687
    database="neo4j",
)
storage_context = StorageContext.from_defaults(graph_store=graph_store)
# 이후 동일하게 KnowledgeGraphIndex.from_documents(...) 사용
"""
