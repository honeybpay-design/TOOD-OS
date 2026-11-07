import pathlib
import time

import psycopg
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.ai_gateway.errors import AIProviderUnavailable
from app.core.config import settings
from app.routes import admin_router, router
from app.routes_oauth import oauth_router
from app.services.parsing import initialize_parsers

app = FastAPI(title="TOOD-OS API", version="0.2.0")


@app.exception_handler(AIProviderUnavailable)
async def ai_provider_unavailable_handler(request: Request, exc: AIProviderUnavailable):
    return JSONResponse(
        status_code=503, content={"detail": "AI generation is temporarily unavailable"}
    )


# CORS — allow requests from tood.uk and api.tood.uk (browser-side fetch)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tood.uk",
        "https://www.tood.uk",
        "https://api.tood.uk",
        "https://tood-os.web.app",
        "https://tood-os.firebaseapp.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(admin_router)
app.include_router(oauth_router)
STATIC = pathlib.Path(__file__).parent / "static"
app.mount("/ui", StaticFiles(directory=STATIC, html=True), name="ui")


@app.middleware("http")
async def record_request_latency(request: Request, call_next) -> Response:
    start = time.monotonic()
    response = await call_next(request)
    latency_ms = round((time.monotonic() - start) * 1000)
    try:
        from app.core.monitoring import get_monitor

        get_monitor().record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
    except Exception:  # noqa: BLE001
        pass  # never let monitoring crash the API
    return response


@app.on_event("startup")
async def startup_event() -> None:
    initialize_parsers()
    try:
        from app.core.monitoring import get_monitor

        get_monitor().health_ping()
    except Exception:  # noqa: BLE001
        pass  # never let monitoring crash startup


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/ui/")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


# Alias for environments where GFE intercepts /healthz before it reaches Cloud Run
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}
