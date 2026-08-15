import uuid

from pydantic import BaseModel, ConfigDict, Field


class ImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    status: str
    url: str
    content_type: str = Field(alias="contentType")
    size_bytes: int = Field(alias="sizeBytes")
    sort_order: int = Field(alias="sortOrder")


class UploadImageResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: ImageResponse


class DeleteImageData(BaseModel):
    deleted: bool = True


class DeleteImageResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: DeleteImageData
