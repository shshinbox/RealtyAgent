import yaml
from functools import lru_cache
from typing import Any
import importlib.resources


class AgentSpecLoader:
    PROMPTS_DIR = importlib.resources.files("engine") / "statics"

    @staticmethod
    @lru_cache(maxsize=32)
    def load_yaml(agent_name: str) -> dict:
        name_str = getattr(agent_name, "value", agent_name)
        file_name = f"{name_str}.yaml"
        file_item = AgentSpecLoader.PROMPTS_DIR / file_name

        if not file_item.is_file():
            raise FileNotFoundError(f"Prompt file not found: {file_name}")

        try:
            content = file_item.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            return data.get(name_str, {})
        except Exception as e:
            raise ValueError(f"Failed to parse YAML for {name_str}: {e}")

    @classmethod
    def load_elements(cls, agent_name: str, element: str, version: str = "v1.0") -> Any:
        data = cls.load_yaml(agent_name)
        val = data.get(version, {}).get(element)
        if val in (None, "", [], {}):
            raise ValueError(
                f"Missing required element '{element}' for agent '{agent_name}'"
            )
        return val

    @classmethod
    def load_prompt(cls, agent_name: str, version: str = "v1.0") -> str:
        return cls.load_elements(agent_name, "template", version)

    @classmethod
    def load_description(cls, agent_name: str, version: str = "v1.0") -> str:
        return cls.load_elements(agent_name, "description", version)

    @classmethod
    def load_tool_argument_prompt(cls, agent_name: str, version: str = "v1.0") -> str:
        return cls.load_elements(agent_name, "tool_argument_template", version)

    @staticmethod
    @lru_cache(maxsize=32)
    def load_generator_yaml(document_type: str) -> dict:
        file_name = f"{document_type}.yaml"
        file_item = AgentSpecLoader.PROMPTS_DIR / "generator" / file_name

        if not file_item.is_file():
            raise FileNotFoundError(
                f"Generator template not found: generator/{file_name}"
            )

        try:
            content = file_item.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            return data.get(document_type, {})
        except Exception as e:
            raise ValueError(f"Failed to parse generator YAML for {document_type}: {e}")

    @classmethod
    def load_prompt_by_document_type(cls, document_type: str, version: str = "v1.0") -> str:
        data = cls.load_generator_yaml(document_type)
        val = data.get(version, {}).get("template")
        if not val:
            raise ValueError(
                f"Missing template for document_type='{document_type}', version='{version}'"
            )
        return val
