# RealtyAgent Project Structure

이 프로젝트는 에이전트 오케스트레이션 엔진과 서비스 게이트웨이로 구성되어 있습니다. 상세 명세는 각 디렉토리의 리드미를 참조하십시오.

### 🧩 [LangGraph Module](./engine/README.md)

### ⚡ [FastAPI Gateway](./server/README.md)

---

<br><br><br>

### To-Do List


#### 2029.02.04

#### 1. Worker Package
- [ ] Redis Queue 메시지 리스너 구현
- [ ] GLiNER 기반 엔티티 추출 워커 로직 작성

#### 2. LangGraph Package
- [ ] Finalizer 노드: Task 발행 로직 추가
- [ ] Vector DB: 대화 내역 저장
- [ ] GLiNER: 키워드 추출 및 저장

#### 3. RAG Module
- [ ] 대화 히스토리 조회용 RAG 노드 설계
- [ ] Retrieval 기반 컨텍스트 주입 로직 구현