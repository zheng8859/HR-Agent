"""ORM 模型聚合导出：导入即完成 mapper 注册，供 Alembic 与 create_all 使用。"""
from app.models.base import Base, BaseModel
from app.models.conversation import Conversation, ConversationStatus
from app.models.document import Document
from app.models.interview_plan import InterviewPlan
from app.models.jd_status import JDStatus
from app.models.job_description import JobDescription
from app.models.knowledge_base import KnowledgeBase
from app.models.message import Message, MessageRole
from app.models.resume_evaluation import ResumeEvaluation, ResumeEvaluationStatus
from app.models.role import Role, user_role
from app.models.scoring_criteria import ScoringCriteria
from app.models.scoring_status import ScoringStatus
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "BaseModel",
    "Conversation",
    "ConversationStatus",
    "Document",
    "InterviewPlan",
    "JDStatus",
    "JobDescription",
    "KnowledgeBase",
    "Message",
    "MessageRole",
    "ResumeEvaluation",
    "ResumeEvaluationStatus",
    "Role",
    "ScoringCriteria",
    "ScoringStatus",
    "User",
    "UserRole",
    "user_role",
]
