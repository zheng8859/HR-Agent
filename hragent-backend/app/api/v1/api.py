"""API v1 路由聚合。"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    documents,
    interview_plans,
    job_descriptions,
    knowledge_assistant,
    knowledge_base,
    resume_evaluation,
    roles,
    scoring_criteria,
    stats,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(job_descriptions.router)
api_router.include_router(scoring_criteria.router)
api_router.include_router(resume_evaluation.router)
api_router.include_router(interview_plans.router)
api_router.include_router(knowledge_base.router)
api_router.include_router(documents.router)
api_router.include_router(knowledge_assistant.router)
api_router.include_router(stats.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
