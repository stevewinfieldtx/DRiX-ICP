from fastapi import APIRouter

from app.api.routes import (
    analytics,
    api_keys,
    auth,
    billing,
    documents,
    external,
    leads,
    projects,
    rubric,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(analytics.router)
api_router.include_router(projects.router)
api_router.include_router(documents.router)
api_router.include_router(rubric.router)
api_router.include_router(leads.router)
api_router.include_router(api_keys.router)
api_router.include_router(external.router)
api_router.include_router(billing.router)
