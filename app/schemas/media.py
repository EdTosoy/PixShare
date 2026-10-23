from pydantic import BaseModel, Field


class ImageVariant(BaseModel):
    url: str
    width: int = Field(gt=0, le=1920)
    height: int = Field(gt=0, le=1920)


class ImageInfo(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    variants: list[ImageVariant]
