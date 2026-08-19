from pydantic import BaseModel, Field


class AiPreferencesUpdate(BaseModel):
    personal_memory_enabled: bool = Field(alias="personalMemoryEnabled")


class AiPreferencesData(BaseModel):
    personal_memory_enabled: bool = Field(alias="personalMemoryEnabled")


class AiPreferencesResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: AiPreferencesData


class DeleteCurrentUserData(BaseModel):
    deleted: bool = True


class DeleteCurrentUserResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: DeleteCurrentUserData
