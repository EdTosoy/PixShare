from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Pix-Share"
    app_version: str = "1.0.0"
    environment: str = "development"
    database_url: str

    uploads_dir: str = "uploads"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    clerk_publishable_key: str = ""
    clerk_secret_key: str = ""
    clerk_jwt_key: str | None = None

    clerk_authorized_parties: Annotated[
        list[str],
        NoDecode,
    ] = Field(default_factory=list)

    @field_validator("clerk_jwt_key", mode="before")
    @classmethod
    def blank_jwt_key(cls, value: str | None) -> str | None:
        return value if value and value.strip() else None

    @field_validator("clerk_authorized_parties", "cors_origins", mode="before")
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
