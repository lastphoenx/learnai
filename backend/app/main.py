from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.admin_pedagogy import router as admin_pedagogy_router
from app.api.admin_task_type_golden import router as admin_task_type_golden_router
from app.api.admin_unit_report import router as admin_unit_report_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.profiles import router as profiles_router
from app.api.routes import auth_router, users_router
from app.api.units import records_router, router as units_router
from app.ai.routes import router as ai_router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
    force=True,
)

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(self), geolocation=()",
    "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            if key not in response.headers:
                response.headers[key] = value
        return response


app = FastAPI(
    title="LearnAI API",
    version="0.5.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(admin_pedagogy_router, prefix="/api/v1")
app.include_router(admin_task_type_golden_router, prefix="/api/v1")
app.include_router(admin_unit_report_router, prefix="/api/v1")
app.include_router(profiles_router, prefix="/api/v1")
app.include_router(units_router, prefix="/api/v1")
app.include_router(records_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")


@app.on_event("startup")
def _validate_production_settings() -> None:
    if settings.is_production:
        _log = logging.getLogger(__name__)
        if not settings.cookie_secure:
            raise RuntimeError("APP_ENV=production erfordert COOKIE_SECURE=true")
        _log.info("Production-Modus: COOKIE_SECURE aktiv")
