import os
from pydantic_settings import SettingsConfigDict
from server.config import Settings


def load_settings() -> Settings:
    app_env = os.getenv("APP_ENV")

    if app_env not in ("local", "docker"):
        raise ValueError("APP_ENV must be one of 'local', 'docker'.")

    env_files = ("server/.env", f"server/.env.{app_env}")

    class AppSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=env_files,
            env_file_encoding="utf-8",
            extra="ignore",
        )

    return AppSettings()
