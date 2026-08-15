import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
WECHAT_CODE_TO_SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


class WechatAuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


async def exchange_code_for_openid(code: str) -> str:
    settings = get_settings()
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise WechatAuthError("AUTH_NOT_CONFIGURED", "微信登录尚未配置", 503)

    params = {
        "appid": settings.wechat_app_id,
        "secret": settings.wechat_app_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(WECHAT_CODE_TO_SESSION_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("wechat_login_upstream_failed error_type=%s", type(exc).__name__)
        raise WechatAuthError("AUTH_UPSTREAM_ERROR", "微信登录服务暂时不可用", 502) from exc

    if payload.get("errcode"):
        logger.info("wechat_login_rejected errcode=%s", payload.get("errcode"))
        raise WechatAuthError("AUTH_INVALID", "微信登录凭证无效", 401)

    open_id = payload.get("openid")
    if not open_id:
        raise WechatAuthError("AUTH_UPSTREAM_ERROR", "微信登录响应异常", 502)
    return open_id
