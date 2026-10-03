# Proposal

## Why

招聘线（JD → 评分标准 → 简历评估 → 面试方案）已闭环，但知识助理模块尚未落地：企业制度、政策、流程文档无法入库，员工也无从基于企业自身文档问答。本变更为知识助理打地基——文档处理管线（上传 → 提取 → 语义切片 → 向量化入 pgvector）与知识库 CRUD。

## What Changes

- 新增文档处理管线：上传（SHA256 哈希 + 落盘 uploads）→ 文本提取（PDF/DOC/DOCX/TXT）→ 语义切片（每段 ≤500 字、严禁 >800，超长强制切分、过短合并）→ Embedding 向量化（1536 维）→ 写入 pgvector。
- 文档状态机：`uploaded → processing → processed / failed`；解析失败有明确提示，支持重新处理。
- 知识库 CRUD：`name` 唯一、`description`、`is_public`、`is_searchable`、`meta_data`、`document_count`、`category`、`tags`；删除知识库前检查是否含文档。
- 删除同步清理：删文档同步清理其切片与向量，删除后不再被检索。
- 文档按 `user_id` 隔离（collection 按用户划分，跨用户不可检索）。

## Capabilities

### New Capabilities

- `doc-kb`: 文档处理与知识库后端能力（上传哈希、文本提取、语义切片、向量化入 pgvector、状态机、知识库 CRUD、删除级联、用户隔离）。

### Modified Capabilities

<!-- 无 -->

## Impact

- `hragent-backend/app/models/document.py`（修改）：新增 `status` 状态列 + `DocumentStatus` 枚举 + `chunk_count`。
- `hragent-backend/app/core/config.py`（修改）：新增上传目录/格式/大小/Embedding 维度/切片参数配置。
- `hragent-backend/app/services/embedding_service.py`（新增实现）：1536 维向量化（mock 确定性向量）。
- `hragent-backend/app/services/enhanced_document_service.py`（新增实现）：上传/哈希/提取/切片/向量化/状态机/删除级联。
- `hragent-backend/app/schemas/document.py` + `knowledge_base.py`（新增实现）。
- `hragent-backend/app/api/v1/endpoints/documents.py` + `knowledge_base.py`（新增实现）。
- `hragent-backend/app/api/v1/api.py`（修改）：注册 `/documents`、`/knowledge-base` 路由。
- `hragent-backend/tests/`（新增）：文档处理与知识库测试。
- 无前端改动（前端在 Phase B 独立变更）。
