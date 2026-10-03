"""API v1 路由聚合。"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    job_descriptions,
    resume_evaluation,
    scoring_criteria,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(job_descriptions.router)
api_router.include_router(scoring_criteria.router)
api_router.include_router(resume_evaluation.router)
