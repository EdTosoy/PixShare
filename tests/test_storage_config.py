from unittest.mock import patch

import pytest
from botocore.exceptions import EndpointConnectionError
from pydantic import SecretStr

from app.storage.base import StorageUnavailable
from app.storage.router import MediaStorage
from tests.helpers.settings import IsolatedSettings as Settings


def test_local_default_needs_no_s3_credentials():
    settings = Settings(database_url="postgresql+asyncpg://localhost/config_test")
    storage = MediaStorage(settings)
    assert storage.provider == "local" and storage.s3 is None
    assert storage.public_url("/uploads/legacy.jpg") == "/uploads/legacy.jpg"
    assert storage.public_url("https://legacy.example/image.jpg") == "https://legacy.example/image.jpg"


@pytest.mark.parametrize("base", ["", "ftp://cdn.example", "https://private:private@cdn.example", "https://cdn.example/?token=value", "https://cdn.example/../other", "https://cdn.example/#fragment"])
def test_invalid_public_base_is_rejected_without_exposing_input(base: str):
    with pytest.raises(ValueError) as error:
        _ = Settings(database_url="postgresql://localhost/config_test", storage_provider="s3", s3_bucket="media-test", s3_public_base_url=base)
    assert "private:private" not in str(error.value)


@pytest.mark.parametrize("prefix", ["", "../other", "media/../other", "media//other", "media?query", "media%2fother"])
def test_unsafe_prefix_is_rejected(prefix: str):
    with pytest.raises(ValueError):
        _ = Settings(database_url="postgresql://localhost/config_test", s3_prefix=prefix)


def test_production_requires_https_and_paired_credentials():
    with pytest.raises(ValueError):
        _ = Settings(database_url="postgresql://localhost/config_test", environment="production", storage_provider="s3", s3_bucket="media-test", s3_public_base_url="http://cdn.example")
    with pytest.raises(ValueError):
        _ = Settings(database_url="postgresql://localhost/config_test", s3_access_key_id=SecretStr("not-a-real-key"))


def test_role_credentials_and_secret_repr():
    settings = Settings(database_url="postgresql://localhost/config_test", storage_provider="s3", s3_bucket="media-test", s3_public_base_url="https://cdn.example", s3_access_key_id=SecretStr("fake-key-for-test"), s3_secret_access_key=SecretStr("fake-secret-for-test"))
    assert "fake-key-for-test" not in repr(settings)
    assert "fake-secret-for-test" not in repr(settings)
    role = Settings(database_url="postgresql://localhost/config_test", storage_provider="s3", s3_bucket="media-test", s3_public_base_url="https://cdn.example")
    assert role.s3_access_key_id is None and role.s3_secret_access_key is None


def test_client_initialization_failure_withholds_sdk_details():
    settings = Settings(database_url="postgresql://localhost/config_test", storage_provider="s3", s3_bucket="media-test", s3_public_base_url="https://cdn.example")
    with patch("app.storage.s3.boto3.client", side_effect=EndpointConnectionError(endpoint_url="https://private-diagnostic.invalid")), pytest.raises(StorageUnavailable) as error:
        _ = MediaStorage(settings)
    assert "private-diagnostic" not in str(error.value)
