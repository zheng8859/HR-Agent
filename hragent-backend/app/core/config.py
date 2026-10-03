"""应用配置（骨架占位）。生产环境必须替换默认密钥与 DB 密码（见 17 生产化要点）。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # 数据库
    database_url: str = "postgresql+asyncpg://hragent:hragent_dev_password@localhost:5432/hragent"

    # 安全
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 小时

    # RAG
    rag_min_similarity_score: float = 0.2

    # Dify（未配置时各服务走 mock，见 36 文档前置检查）
    dify_base_url: str = ""
    dify_api_key: str = ""
    dify_jd_workflow_id: str = ""       # type=1 JD 生成
    dify_scoring_workflow_id: str = ""  # type=2 评分标准生成
    dify_resume_workflow_id: str = ""   # type=3 简历评估
    dify_interview_workflow_id: str = ""  # type=4 面试方案
    dify_timeout_seconds: int = 60

    # 简历上传限制（doc 37：PDF/DOC/DOCX，默认 ≤10MB，服务端强制）
    resume_max_size_mb: int = 10
    resume_allowed_types: str = "pdf,doc,docx"

    # 文档上传与知识库（doc 39：PDF/DOC/DOCX/TXT，默认 ≤20MB，服务端强制）
    upload_dir: str = "uploads"
    document_max_size_mb: int = 20
    document_allowed_types: str = "pdf,doc,docx,txt"

    # Embedding（未配置时 embedding_service 走确定性 mock）
    embedding_dimension: int = 1536
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"

    # 语义切片参数（doc 39：每段 ≤500、严禁 >800、超长强制切分、过短合并）
    chunk_max_chars: int = 500
    chunk_force_split_chars: int = 800
    chunk_min_chars: int = 50

    @property
    def dify_configured(self) -> bool:
        return bool(self.dify_base_url and self.dify_api_key)

    @property
    def embedding_configured(self) -> bool:
        return bool(self.embedding_base_url and self.embedding_api_key)


settings = Settings()
