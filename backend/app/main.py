import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.diaries import router as diaries_router
from app.api.health import router as health_router
from app.api.reflections import router as reflections_router
from app.api.uploads import router as uploads_router
from app.api.users import router as users_router
from app.core.logging import configure_logging, request_id_context
from app.core.rate_limit import check_rate_limit

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="NanNan API", version="0.1.0")
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(diaries_router, prefix="/api/v1")
app.include_router(reflections_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    supplied_request_id = request.headers.get("x-request-id", "")
    request_id = (
        supplied_request_id
        if supplied_request_id and len(supplied_request_id) <= 128
        else str(uuid.uuid4())
    )
    token = request_id_context.set(request_id)
    started = time.perf_counter()
    client = request.client.host if request.client else "unknown"
    status_code = 500
    try:
        if request.url.path.startswith("/api/v1/") and request.url.path != "/api/v1/health":
            rate = await check_rate_limit(client)
            if not rate.allowed:
                status_code = 429
                response = JSONResponse(
                    status_code=429,
                    content={
                        "code": "RATE_LIMITED",
                        "message": "请求过于频繁，请稍后重试",
                        "data": None,
                    },
                    headers={"Retry-After": str(rate.retry_after)},
                )
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "method": request.method,
                "path": request.url.path,
                "status": status_code,
                "latency_ms": latency_ms,
                "client": client,
            },
        )
        request_id_context.reset(token)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", "请求失败")
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": message, "data": None},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    fields = [
        ".".join(str(part) for part in error["loc"] if part != "body")
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求参数不符合要求",
            "data": {"fields": fields},
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_request_error error_type=%s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "服务暂时不可用", "data": None},
    )

@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": "nannan", "status": "ok"}
