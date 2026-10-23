from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.media import ImageInfo


class PostResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    caption: str | None
    url: str
    file_name: str
    file_type: str
    created_at: datetime
    updated_at: datetime
    image: ImageInfo | None = None
