from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    REDIS_URL: str | None = Field(default=None)
    OPENAI_API_KEY: str | None = Field(default=None)
    SECRET_KEY: str | None = Field(default=None)
    ALGORITHM: str = Field(default="HS256")
    QDRANT_HOST: str | None = Field(default=None)
    QDRANT_PORT: int | None = Field(default=None)
    POSTGRESQL_URL: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        extra="ignore",
    )
