from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.core.config import settings
from app.core.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
app.add_middleware(
    SecurityHeadersMiddleware,
    production=settings.environment == "production",
)

app.include_router(health_router)
app.include_router(intake_router, prefix=settings.api_prefix)
app.include_router(guide_mapping_router, prefix=settings.api_prefix)
app.include_router(scene_manifests_router, prefix=settings.api_prefix)
app.include_router(simulation_plans_router, prefix=settings.api_prefix)
app.include_router(runs_router, prefix=settings.api_prefix)
app.include_router(research_objects_router, prefix=settings.api_prefix)
app.include_router(provenance_router, prefix=settings.api_prefix)
app.include_router(results_router, prefix=settings.api_prefix)
app.include_router(rag_router, prefix=settings.api_prefix)
