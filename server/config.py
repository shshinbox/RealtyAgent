from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


app_env = os.getenv("APP_ENV")

if app_env not in ("local", "docker"):
    raise ValueError("APP_ENV must be one of 'local', 'docker'.")


class Settings(BaseSettings):
    REDIS_URL: str | None = Field(default=None)
    OPENAI_API_KEY: str | None = Field(default=None)
    SECRET_KEY: str | None = Field(default=None)
    ALGORITHM: str = Field(default="HS256")
    QDRANT_HOST: str | None = Field(default=None)
    QDRANT_PORT: int | None = Field(default=None)
    POSTGRESQL_DSN: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=("server/.env", f"server/.env.{app_env}"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
