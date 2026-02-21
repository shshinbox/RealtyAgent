# RealtyAgent Project Structure

이 프로젝트는 에이전트 오케스트레이션 엔진과 서비스 게이트웨이로 구성되어 있습니다.

### 🧩 [LangGraph Module](./engine/README.md)

### ⚡ [FastAPI Gateway](./server/README.md)

---

<br><br>

# TO-DO LIST


### 1. 문서 RAG 최적화 전략

단순 청킹의 정보 손실을 방지하고 검색 정확도를 높이기 위해 아래 후보군 중에서 검토 중

* **문맥 주입형 검색 (Contextual Retrieval):** 각 청크에 문서 전체 요약 정보를 메타데이터로 삽입
* **그래프 기반 검색 (GraphRAG):** 문서 내 개체 간 관계를 추출하여 그래프 데이터베이스화, 단순 유사도 검색으로 불가능한 다단계 추론 대응

---

### 2. 사용자 맥락 및 메모리 관리 전략

사용자의 대화 흐름을 기억하고 세션이 바뀌어도 개인화된 응답을 유지하기 위해 아래 구조를 적용

* **대화 이력:** 사용자 질의와 모델 응답 세트를 벡터 데이터베이스에 저장, 새로운 세션에서도 과거 맥락을 조회 가능
* **정형 구조 장기 메모리:** GLiNER(DeBERTa-v3 기반)를 활용해 대화 중 주요 키워드 추출, 사용자 프로필 및 제약 사항 관리용


---


#### a. Worker Package
- [ ] Redis Queue 메시지 리스너 구현
- [x] GLiNER 기반 엔티티 추출 워커 로직 작성

#### b. LangGraph Package
- [x] Finalizer 노드: Task 발행 로직 추가
- [x] Vector DB: 대화 내역 저장
- [x] GLiNER: 키워드 추출

#### c. RAG module
- [x] 대화 히스토리 조회용 RAG 노드 설계
- [ ] Retrieval 기반 컨텍스트 주입 로직 구현