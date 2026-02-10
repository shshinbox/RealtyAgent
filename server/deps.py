from fastapi import Request
from .config import Settings


def get_settings(request: Request) -> Settings:
    settings = request.app.state.settings

    if settings is None:
        raise RuntimeError("Settings not loaded in app.state")

    return settings
