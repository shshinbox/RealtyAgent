import pytest
from worker.extractor import PersonaExtractor


def test_persona_extractor_real():
    print("\n[Test] Starting PersonaExtractor test...")
    extractor = PersonaExtractor()

    test_text = "서대문구에서 10억 정도로 조용한 아파트 알아보고 있어."
    result = extractor.extract(test_text)

    assert "location" in result
    assert "budget" in result

    print(f"\n[Test Result] Extracted: {result}")
