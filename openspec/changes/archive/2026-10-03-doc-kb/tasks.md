# Tasks

## 1. 模型与配置

- [x] 1.1 `app/models/document.py` 新增 `DocumentStatus` 枚举 + `status` 列 + `chunk_count` 列；生成 Alembic 迁移。验证：建表成功。
- [x] 1.2 `app/core/config.py` 新增上传目录/格式/大小/Embedding 维度/切片参数。验证：默认值正确。

## 2. 服务

- [x] 2.1 `app/services/embedding_service.py`：`embed_text`（mock 1536 维 + 真实 API 钩子）。验证：维度 1536。
- [x] 2.2 `app/services/enhanced_document_service.py`：`chunk_text`（语义切片）、`compute_sha256`、`validate_document`、`extract_text`、上传/处理/重新处理/查询/删除（级联 + 所有权）。验证：哈希/切片/状态机/删除级联。

## 3. Schema 与端点

- [x] 3.1 `app/schemas/document.py` + `knowledge_base.py`：请求/响应。验证：校验通过。
- [x] 3.2 `app/api/v1/endpoints/knowledge_base.py`：CRUD（唯一名 + 含文档 409）。验证：CRUD 正常。
- [x] 3.3 `app/api/v1/endpoints/documents.py`：upload/list/get/chunks/reprocess/delete。验证：上传/状态/切片/删除。
- [x] 3.4 `app/api/v1/api.py` 注册 `/knowledge-base`、`/documents` 路由。验证：可访问。

## 4. 测试

- [x] 4.1 `tests/test_document_service.py`：哈希、提取、切片（超长/过短）、向量化 1536、状态机、删除级联、所有权。
- [x] 4.2 `tests/test_knowledge_base_service.py`：CRUD、名称唯一、含文档拒绝删除。
- [x] 4.3 `tests/test_document_endpoints.py` + `test_knowledge_base_endpoints.py`：RBAC、上传校验、隔离。
