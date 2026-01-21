from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from typing import Any

from ..graph.logger import logger


class PresidioKoreanEngine:
    def __init__(self) -> None:
        self.configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "ko", "model_name": "ko_core_news_lg"}],
        }
        self.provider = NlpEngineProvider(nlp_configuration=self.configuration)
        self.nlp_engine = self.provider.create_engine()
        self.analyzer = AnalyzerEngine(
            nlp_engine=self.nlp_engine, default_score_threshold=0.4
        )
        self.anonymizer = AnonymizerEngine()
        self._add_korean_recognizers()

    def _add_korean_recognizers(self) -> None:
        rrn_pattern = Pattern(name="rrn_pattern", regex=r"\d{6}-[1-4]\d{6}", score=0.8)
        rrn_recognizer = PatternRecognizer(
            supported_entity="KR_RRN",
            patterns=[rrn_pattern],
            context=["주민등록번호", "주민번호", "RRN"],
        )

        ko_phone_pattern = Pattern(
            name="ko_phone_pattern", regex=r"01[016789]-\d{3,4}-\d{4}", score=0.7
        )
        ko_phone_recognizer = PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            patterns=[ko_phone_pattern],
            context=["전화번호", "휴대폰", "연락처", "폰"],
        )
        self.analyzer.registry.add_recognizer(rrn_recognizer)
        self.analyzer.registry.add_recognizer(ko_phone_recognizer)

    async def process(self, text: str, entities: list | None = None) -> dict[str, Any]:
        try:
            return await self._process(text=text, entities=entities)
        except Exception as e:
            logger.warning(f"HallucinationDetector failed. error: {str(e)}")
            return {
                "is_pii": False,
                "masked_text": "",
                "detected_entities": [],
            }

    async def _process(self, text: str, entities: list | None = None) -> dict[str, Any]:
        """
        :param text: 처리할 전체 텍스트
        :param entities: 탐지할 엔티티 리스트 (None일 경우 전체 탐지)
        :return: {'is_pii': bool, 'masked_text': str, 'detected_entities': list}
        """
        analyzer_results = self.analyzer.analyze(
            text=text, language="ko", entities=entities
        )

        is_pii: bool = len(analyzer_results) > 0
        detected_types: list = list(set([res.entity_type for res in analyzer_results]))

        anonymized_result = self.anonymizer.anonymize(
            text=text, analyzer_results=analyzer_results  # type: ignore
        )

        return {
            "is_pii": is_pii,
            "masked_text": anonymized_result.text,
            "detected_entities": detected_types,
        }
