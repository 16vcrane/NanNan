from pydantic import BaseModel


class DeleteCurrentUserData(BaseModel):
    deleted: bool = True


class DeleteCurrentUserResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: DeleteCurrentUserData
