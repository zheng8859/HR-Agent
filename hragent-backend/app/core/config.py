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

    # RAG 检索（doc 40：向量 + tsvector 全文，0.7/0.3 加权，阈值过滤）
    rag_min_similarity_score: float = 0.2
    rag_top_k: int = 5              # 进入生成/重排的候选文档数
    rag_source_chunks: int = 3      # 返回给前端的来源片段数
    rag_vector_weight: float = 0.7  # 向量分权重
    rag_text_weight: float = 0.3    # 全文（tsvector）分权重

    # LLM（Qwen）：走库判断 / 查询改写 / 答案生成；未配置时 llm_service 走确定性 mock
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "qwen-turbo"

    # Rerank（gte-rerank-v2）：检索重排；未配置或调用失败时降级为原始召回排序
    rerank_base_url: str = ""
    rerank_api_key: str = ""
    rerank_model: str = "gte-rerank-v2"
    rerank_top_k: int = 5

    # Dify（方案 A：单应用单 API Key，靠 inputs.type=1~4 在应用内分支；未配置时各服务走 mock）
    dify_base_url: str = ""
    dify_api_key: str = ""
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

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_base_url and self.llm_api_key)

    @property
    def rerank_configured(self) -> bool:
        return bool(self.rerank_base_url and self.rerank_api_key)


settings = Settings()
