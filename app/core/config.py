from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Pix-Share"
    app_version: str = "1.0.0"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = Field(repr=False)
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=50)
    database_timeout: float = Field(default=5, gt=0, le=30)
    database_command_timeout: float = Field(default=15, gt=0, le=120)
    readiness_timeout: float = Field(default=3, gt=0, le=10)
    api_max_body_bytes: int = Field(default=11 * 1024 * 1024, ge=10 * 1024 * 1024 + 65536, le=16 * 1024 * 1024)
    request_body_timeout: float = Field(default=30, gt=0, le=120)
    api_read_limit: int = Field(default=300, ge=1, le=10000)
    api_write_limit: int = Field(default=60, ge=1, le=1000)
    allowed_hosts: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "test"])

    uploads_dir: str = "uploads"
    storage_provider: Literal["local", "s3"] = "local"
    s3_bucket: str = ""
    s3_prefix: str = "pixshare/media"
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_public_base_url: str = ""
    s3_addressing_style: Literal["auto", "path", "virtual"] = "auto"
    s3_access_key_id: SecretStr | None = Field(default=None, repr=False)
    s3_secret_access_key: SecretStr | None = Field(default=None, repr=False)
    s3_session_token: SecretStr | None = Field(default=None, repr=False)
    s3_connect_timeout: float = Field(default=3, gt=0, le=60)
    s3_read_timeout: float = Field(default=10, gt=0, le=60)
    s3_max_attempts: int = Field(default=3, ge=1, le=5)
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    clerk_publishable_key: str = ""
    clerk_secret_key: str = Field(default="", repr=False)
    clerk_jwt_key: str | None = None

    clerk_authorized_parties: Annotated[
        list[str],
        NoDecode,
    ] = Field(default_factory=list)

    @field_validator("clerk_jwt_key", mode="before")
    @classmethod
    def blank_jwt_key(cls, value: str | None) -> str | None:
        return value if value and value.strip() else None

    @field_validator("s3_endpoint_url", "s3_access_key_id", "s3_secret_access_key", "s3_session_token", mode="before")
    @classmethod
    def blank_s3_value(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def validate_storage(self):
        import re

        self.s3_prefix = self.s3_prefix.strip("/")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*", self.s3_prefix):
            raise ValueError("S3_PREFIX must contain safe nonempty path segments")
        if bool(self.s3_access_key_id) != bool(self.s3_secret_access_key):
            raise ValueError("Supply both S3 credential fields or use the server's AWS credential chain")
        if self.storage_provider == "s3" or self.s3_bucket:
            if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", self.s3_bucket):
                raise ValueError("A valid S3_BUCKET is required")
            for value in [self.s3_public_base_url, self.s3_endpoint_url]:
                if value is None:
                    continue
                parsed = urlsplit(value)
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.query
                    or parsed.fragment
                    or any(part in {".", ".."} for part in parsed.path.split("/"))
                ):
                    raise ValueError("S3 endpoint/public base must be an HTTP(S) URL without credentials, queries or traversal")
                if self.environment == "production" and parsed.scheme != "https":
                    raise ValueError("Production S3 endpoint/public base must use HTTPS")
            self.s3_public_base_url = self.s3_public_base_url.rstrip("/")
        return self

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment != "production":
            return self
        if not (self.clerk_secret_key.startswith("sk_live_") or self.clerk_jwt_key):
            raise ValueError("Production requires a live Clerk server key or JWT verification public key")
        if self.clerk_secret_key and not self.clerk_secret_key.startswith("sk_live_"):
            raise ValueError("Development Clerk keys are not permitted in production")
        for origins in [self.cors_origins, self.clerk_authorized_parties]:
            if not origins:
                raise ValueError("Production CORS and Clerk authorized origins must be explicit and nonempty")
            for origin in origins:
                parsed = urlsplit(origin)
                if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment or "*" in origin
                    or parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
                    raise ValueError("Production origins must be exact public HTTPS origins")
        if not set(self.cors_origins).issubset(self.clerk_authorized_parties):
            raise ValueError("Every production CORS origin must be a Clerk authorized party")
        if not self.allowed_hosts or any(not host or "*" in host or host in { "localhost", "127.0.0.1", "test"} or "/" in host or ":" in host for host in self.allowed_hosts):
            raise ValueError("Production ALLOWED_HOSTS must list explicit API hostnames")
        return self

    @field_validator("clerk_authorized_parties", "cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def split_csv(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]

        return value

    model_config = SettingsConfigDict(  # pyright: ignore[reportUnannotatedClassAttribute]
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
