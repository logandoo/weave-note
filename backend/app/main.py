"""Weave Note 服务入口 — 代码组装自 chatbot（仅解耦裁剪）。

Deployment:
    cd weave-note/backend
    /tmp/weave-family-venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8201
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select, text

from app.api import auth, export_tasks, file_upload, image_upload, notes
from app.core.config import get_config
from app.db.database import AsyncSessionLocal, Notebook, User, init_db
from app.services.auth_service import hash_password
from app.services.export_worker import export_worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

config = get_config()
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not config.security_jwt_secret_key:
        raise RuntimeError("JWT secret key is not configured")

    backend_dir = os.path.dirname(__file__)
    os.makedirs(os.path.join(backend_dir, "audio_files"), exist_ok=True)
    os.makedirs(os.path.join(backend_dir, "output_files"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(backend_dir), "Fonts"), exist_ok=True)
    await init_db()
    await _ensure_test_user()
    await export_worker.start()
    logger.info("Weave Note 启动完成")
    yield
    await export_worker.stop()


app = FastAPI(title="Weave Note", version="1.0.0", docs_url=None, redoc_url=None, openapi_url="/openapi.json", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        msg = str(err.get("msg", "invalid")).replace("Value error, ", "")
        messages.append(f"{loc}: {msg}" if loc else msg)
    return JSONResponse(status_code=422, content={"detail": "；".join(messages)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security_cors_allow_origins,
    allow_credentials=config.security_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(export_tasks.router)
app.include_router(image_upload.router)
app.include_router(file_upload.router)


async def _ensure_test_user() -> None:
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.username == "test"))).scalar_one_or_none()
        if user is None:
            user = User(username="test", password_hash=await hash_password("123456"), role="user")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("已创建默认测试账号 test / 123456")
        notebook = (await db.execute(select(Notebook).where(Notebook.user_id == user.id, Notebook.is_default.is_(True)))).scalar_one_or_none()
        if notebook is None:
            db.add(Notebook(user_id=user.id, name="默认笔记本", is_default=True))
            await db.commit()
            logger.info("已创建默认笔记本")


@app.get("/healthz")
async def healthz() -> dict:
    db_ok = False
    error = None
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # pragma: no cover
        error = str(exc)
    payload = {"status": "ok" if db_ok else "degraded", "service": "weave-note", "database": "ok" if db_ok else "error"}
    if error:
        payload["error"] = error
    return payload


@app.get("/api/health")
async def api_health() -> dict:
    return await healthz()


@app.get("/{full_path:path}", include_in_schema=False)
async def spa(full_path: str):
    if full_path:
        candidate = (STATIC_DIR / full_path).resolve()
        if str(candidate).startswith(str(STATIC_DIR.resolve()) + "/") and candidate.is_file():
            return FileResponse(candidate)
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index, media_type="text/html", headers={"Cache-Control": "no-store"})
    return {"service": "weave-note", "hint": "前端静态文件尚未构建，请先运行 frontend 部署步骤或直接调用 /api/notes 接口"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False
    )
