from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.storage.base import Storage
from app.storage.local import LocalStorage


@lru_cache
def get_storage() -> Storage:
    return LocalStorage()


StorageDep = Annotated[Storage, Depends(get_storage)]
