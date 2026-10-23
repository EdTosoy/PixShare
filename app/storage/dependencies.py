from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.storage.base import Storage
from app.storage.local import LocalStorage


@lru_cache
def get_storage() -> Storage:
    return LocalStorage(get_settings().uploads_dir)


StorageDep = Annotated[Storage, Depends(get_storage)]
