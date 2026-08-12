from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Pix-Share"
    app_version: str = "1.0.0"
    environment: str = "development"
    database_url: str

    clerk_publishable_key: str
    clerk_secret_key: str
    clerk_jwt_key: str | None = None

    clerk_authorized_parties: Annotated[
        list[str],
        NoDecode,
    ] = Field(default_factory=list)

    @field_validator("clerk_authorized_parties", mode="before")
    @classmethod
    def split_csv(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]

        return value

    model_config = SettingsConfigDict(  # pyright: ignore[reportUnannotatedClassAttribute]
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
