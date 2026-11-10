from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from postgrest.exceptions import APIError
from starlette.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.folders import router as folders_router
from app.api.routes.guide_mapping import router as guide_mapping_router
from app.api.routes.health import router as health_router
from app.api.routes.intake import router as intake_router
from app.api.routes.provenance import router as provenance_router
from app.api.routes.rag import router as rag_router
from app.api.routes.research_objects import router as research_objects_router
from app.api.routes.results import router as results_router
from app.api.routes.runs import router as runs_router
from app.api.routes.scene_manifests import router as scene_manifests_router
from app.api.routes.simulation_plans import router as simulation_plans_router
from app.core.auth import AuthenticationMiddleware
from app.core.config import settings
from app.core.security import (
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.db import BackendSetupError

app = FastAPI(title=settings.app_name)
app.add_middleware(AuthenticationMiddleware)


@app.exception_handler(BackendSetupError)
async def missing_database(request, exc):
    return JSONResponse({"detail": {"code": "database_not_configured"}}, status_code=503)


@app.exception_handler(APIError)
async def database_failure(request, exc):
    missing_schema = exc.code in {"PGRST204", "PGRST205", "42P01", "42703"}
    code = "workspace_setup_required" if missing_schema else "database_unavailable"
    return JSONResponse({"detail": {"code": code}}, status_code=503)

app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_requests_per_minute,
    max_clients=settings.rate_limit_max_clients,
)
app.add_middleware(
    SecurityHeadersMiddleware,
    production=settings.environment == "production",
)
# Last added is outermost: transport rejections must remain readable by the UI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization"],
    expose_headers=["Retry-After"],
)

app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(folders_router, prefix=settings.api_prefix)
app.include_router(intake_router, prefix=settings.api_prefix)
app.include_router(guide_mapping_router, prefix=settings.api_prefix)
app.include_router(scene_manifests_router, prefix=settings.api_prefix)
app.include_router(simulation_plans_router, prefix=settings.api_prefix)
app.include_router(runs_router, prefix=settings.api_prefix)
app.include_router(research_objects_router, prefix=settings.api_prefix)
app.include_router(provenance_router, prefix=settings.api_prefix)
app.include_router(results_router, prefix=settings.api_prefix)
app.include_router(rag_router, prefix=settings.api_prefix)
