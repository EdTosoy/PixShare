from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# class PostCreate(BaseModel):
#     caption: str | None = None
#     url: str
#     file_name: str
#     file_type: str
#
#
class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    caption: str | None
    url: str
    file_name: str
    file_type: str
    created_at: datetime
    updated_at: datetime


class PostUpdate(BaseModel):
    caption: str | None = None
    url: str | None = None
    file_name: str | None = None
    file_type: str | None = None
