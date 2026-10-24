from typing import ClassVar

from pydantic_settings import SettingsConfigDict

from app.core.config import Settings


class IsolatedSettings(Settings):
    """Do not load a developer's private application dotenv during config tests."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(env_file=None)
