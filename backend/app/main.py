from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import admin, auth, communities, posts, social, users
from app.api.deps import Db, csrf_guard
from app.errors import install_error_handlers

API_PREFIX = "/api/v1"

app = FastAPI(
    title="Qauym API",
    version="0.1.0",
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=None,
)
install_error_handlers(app)

router = APIRouter(prefix=API_PREFIX, dependencies=[Depends(csrf_guard)])


@router.get("/health", tags=["health"])
def health(db: Db) -> JSONResponse:
    """Liveness plus a database round trip."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status": "degraded", "database": "unavailable"}, status_code=503)
    return JSONResponse({"status": "ok", "database": "ok"})


for module in (auth, users, posts, social, communities, admin):
    router.include_router(module.router)

app.include_router(router)
