"""应用配置（骨架占位）。生产环境必须替换默认密钥与 DB 密码（见 17 生产化要点）。"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    database_url: str = "postgresql+asyncpg://hragent:hragent_dev_password@localhost:5432/hragent"

    # 安全
    secret_key: str = "change-me-in-production"

    # RAG
    rag_min_similarity_score: float = 0.2

    class Config:
        env_file = ".env"


settings = Settings()
