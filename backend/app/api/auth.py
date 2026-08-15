from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.auth import LoginData, LoginResponse, UserResponse, WechatLoginRequest
from app.services.auth_service import get_or_create_user
from app.services.wechat_service import WechatAuthError, exchange_code_for_openid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: WechatLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    try:
        open_id = await exchange_code_for_openid(payload.code)
    except WechatAuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    user = await get_or_create_user(db, open_id)
    try:
        access_token = create_access_token(user.id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "AUTH_NOT_CONFIGURED", "message": "登录服务尚未配置"},
        ) from exc

    return LoginResponse(
        data=LoginData(
            accessToken=access_token,
            user=UserResponse.from_user(user),
        )
    )
