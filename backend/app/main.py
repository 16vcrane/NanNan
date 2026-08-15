from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.diaries import router as diaries_router
from app.api.health import router as health_router
from app.api.uploads import router as uploads_router
from app.api.users import router as users_router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="NanNan API", version="0.1.0")
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(diaries_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


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

@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": "nannan", "status": "ok"}
