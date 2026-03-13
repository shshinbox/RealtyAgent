# RealtyAgent

부동산 및 법률 상담에 특화된 멀티에이전트 AI 시스템입니다.
기존 선형 워크플로우의 한계를 극복하기 위해 LangGraph 기반으로 고도화된 버전입니다.

> 이전 버전: [real-estate-agent](https://github.com/shshinbox/real-estate-agent)

---

## 문서

### 아키텍처
- [시스템 개요](./docs/architecture/system-overview.md) — 전체 구조, 기술 스택, ExternalDepsPort 인터페이스 설계
- [에이전트 워크플로우](./docs/architecture/agent-workflow.md) — LangGraph 노드 구성 및 실행 흐름
- [저장소 전략](./docs/architecture/storage-strategy.md) — PostgreSQL / Qdrant / Neo4j 역할 정의
- [문서 수집 파이프라인](./docs/architecture/ingestion-pipeline.md) — PDF 수집, GraphRAG, 하이브리드 검색 설계

### API
- [API 레퍼런스](./docs/architecture/api-reference.md) — 엔드포인트 목록 및 인증 방식
