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
    dify_timeout_seconds: int = 60

    @property
    def dify_configured(self) -> bool:
        return bool(self.dify_base_url and self.dify_api_key)


settings = Settings()
