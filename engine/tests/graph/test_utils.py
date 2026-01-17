import pytest
import yaml
from unittest.mock import MagicMock, patch
from engine.graph.utils import AgentSpecLoader


class TestAgentSpecLoader:

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """테스트마다 캐시를 비워 독립성을 보장합니다."""
        AgentSpecLoader.load_yaml.cache_clear()

    # 가상의 YAML 데이터
    MOCK_YAML_CONTENT = """
    planner:
      v1:
        template: "당신은 플래너입니다. 질문: {raw_query}"
        description: "작업 계획 수립 노드"
        tool_argument_template: "도구 인자 생성 템플릿"
    """

    @patch("engine.graph.utils.AgentSpecLoader.PROMPTS_DIR")
    def test_load_yaml_success(self, mock_dir):
        """YAML 파일을 정상적으로 읽어 딕셔너리로 반환하는지 테스트"""
        # 파일 경로 객체 모킹
        mock_file = MagicMock()
        mock_file.is_file.return_value = True
        mock_file.read_text.return_value = self.MOCK_YAML_CONTENT
        mock_dir.__truediv__.return_value = mock_file  # / 연산자 모킹

        result = AgentSpecLoader.load_yaml("planner")

        assert result["v1"]["template"] == "당신은 플래너입니다. 질문: {raw_query}"
        assert "v1" in result

    @patch("engine.graph.utils.AgentSpecLoader.PROMPTS_DIR")
    def test_load_elements_success(self, mock_dir):
        """특정 버전의 특정 요소를 정확히 가져오는지 테스트"""
        mock_file = MagicMock()
        mock_file.is_file.return_value = True
        mock_file.read_text.return_value = self.MOCK_YAML_CONTENT
        mock_dir.__truediv__.return_value = mock_file

        val = AgentSpecLoader.load_elements("planner", "description", "v1")
        assert val == "작업 계획 수립 노드"

    @patch("engine.graph.nodes.base.AgentSpecLoader.load_yaml")
    def test_load_prompt_wrapper(self, mock_load_yaml):
        """load_prompt가 load_elements를 거쳐 정확한 값을 반환하는지 테스트"""
        # load_yaml의 결과만 가짜로 주입 (파일 I/O 생략)
        mock_load_yaml.return_value = yaml.safe_load(self.MOCK_YAML_CONTENT)["planner"]

        prompt = AgentSpecLoader.load_prompt("planner", "v1")
        assert "당신은 플래너입니다" in prompt

    @patch("engine.graph.utils.AgentSpecLoader.PROMPTS_DIR")
    def test_file_not_found(self, mock_dir):
        """파일이 없을 때 FileNotFoundError 발생 확인"""
        mock_file = MagicMock()
        mock_file.is_file.return_value = False
        mock_dir.__truediv__.return_value = mock_file

        with pytest.raises(FileNotFoundError):
            AgentSpecLoader.load_yaml("non_existent_agent")

    @patch("engine.graph.utils.AgentSpecLoader.load_yaml")
    def test_missing_element_error(self, mock_load_yaml):
        """YAML에 정의되지 않은 요소를 요청할 때 ValueError 발생 확인"""
        mock_load_yaml.return_value = {"v1": {"only_template": "hi"}}

        with pytest.raises(ValueError, match="Missing required element 'description'"):
            AgentSpecLoader.load_elements("planner", "description", "v1")
