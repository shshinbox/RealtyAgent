from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class ConfigSettings(BaseSettings):
    KOREAN_LAW_OC: str | None = Field(default=None)
    OPENAI_API_KEY: str | None = Field(default=None)
    LAKERA_GUARD_API_KEY: str | None = Field(default=None)
    UPSTAGE_API_KEY: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file="engine/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


config_settings = ConfigSettings()
