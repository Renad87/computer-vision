"""FastAPI app for the final Poetry Vision product (API in docs/API.md).

    .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8010
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import settings
from .service import STATE, AppError, taxonomy_payload


@asynccontextmanager
async def lifespan(_app):
    if os.environ.get("PV_SKIP_MODEL") != "1":
        STATE.load_model()
    STATE.load_corpus()
    yield


app = FastAPI(title="Poetry Vision", version=settings.APP_VERSION, lifespan=lifespan)


@app.exception_handler(AppError)
async def _app_error(_request: Request, exc: AppError):
    body = {"error": {"code": exc.code, "message_ar": exc.message_ar}}
    if exc.issues:
        body["error"]["issues"] = exc.issues
    return JSONResponse(status_code=exc.status, content=body)


@app.get("/api/health")
def health():
    return {"status": "ok", "app_version": settings.APP_VERSION}


@app.get("/api/ready")
def ready():
    return STATE.readiness()


@app.get("/api/taxonomy")
def taxonomy():
    return taxonomy_payload()


@app.post("/api/analyze")
async def analyze(image: UploadFile = File(...)):
    data = await image.read(settings.MAX_UPLOAD_BYTES + 1)
    if not data:
        raise AppError(400, "empty_file", "الملف فارغ.")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise AppError(413, "too_large", "حجم الصورة أكبر من 15 ميغابايت.")
    return await run_in_threadpool(STATE.analyze, data)


@app.post("/api/recommend")
async def recommend(request: Request):
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        raise AppError(400, "invalid_json", "طلب غير صالح.")
    if not isinstance(body, dict):
        raise AppError(400, "invalid_json", "طلب غير صالح.")
    return STATE.recommend(body)


@app.api_route("/api/{rest:path}", methods=["GET", "POST"])
def api_not_found(rest: str):
    raise AppError(404, "not_found", "مسار غير موجود.")


if os.path.isdir(os.path.join(settings.FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(settings.FRONTEND_DIST, "assets")), name="assets")


@app.get("/{rest:path}")
def spa(rest: str):
    index = os.path.join(settings.FRONTEND_DIST, "index.html")
    candidate = os.path.normpath(os.path.join(settings.FRONTEND_DIST, rest))
    if rest and candidate.startswith(settings.FRONTEND_DIST) and os.path.isfile(candidate):
        return FileResponse(candidate)
    if os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse(status_code=503, content={"error": {"code": "frontend_not_built",
                                                             "message_ar": "الواجهة غير مبنية: شغّل npm run build في frontend/."}})
