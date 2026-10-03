# Design

## 目标

新增文档处理管线与知识库后端，对接 `Document` / `KnowledgeBase` 本地表，实现「上传 → 提取 → 切片 → 向量化 → 状态机 → 删除级联」闭环。

## 端点

| 动作 | 端点 | 权限 |
|------|------|------|
| 新建知识库 | `POST /knowledge-base` → 201 | 写（`get_current_admin_by_role`） |
| 知识库列表 | `GET /knowledge-base` | 读（`get_current_user`） |
| 知识库详情 | `GET /knowledge-base/{id}` | 读 |
| 编辑知识库 | `PUT /knowledge-base/{id}` | 写 |
| 删除知识库 | `DELETE /knowledge-base/{id}` | 写（含文档则 409） |
| 上传文档 | `POST /documents/upload`（multipart）→ 201 | 写 |
| 文档列表 | `GET /documents?knowledge_base_id=` | 读（按 `user_id` 过滤） |
| 文档详情 | `GET /documents/{id}` | 读（所有权） |
| 查看切片 | `GET /documents/{id}/chunks` | 读（所有权） |
| 重新处理 | `POST /documents/{id}/reprocess` | 写 |
| 删除文档 | `DELETE /documents/{id}` | 写 |

## 关键决策

1. **数据模型遵循 doc 35**：`Document.embedding` 为单 `Vector(1536)`，本次**新增** `status`（状态机）与 `chunk_count`（切片数）两列，不新增切片表。语义切片逻辑（`chunk_text`）作为向量化输入预处理与前端「切片数/查看切片」来源；chunk 级检索粒度留待 40 RAG 阶段再评估。
2. **语义切片**：纯函数 `chunk_text(text, max_chars=500, force_split=800, min_chars=50)`——优先按段落/句子边界切分，超长（>800）强制切分，过短（<50）向上合并，保证每段 ≤500 且无 >800。
3. **向量化**：`embedding_service.embed_text(text)` 返回 1536 维向量；未配置 Embedding 密钥时走确定性 mock（对文本 hash 派生固定向量），配置后走真实 API。
4. **状态机**：`uploaded → processing → processed / failed`。上传落库即 `uploaded`；处理（提取+切片+向量化）期间 `processing`，成功 `processed`、失败 `failed`（记录失败原因）；`failed` 可 `reprocess`。
5. **删除级联**：删文档 = 删整行（其向量随行移除），删除后不再被检索；删知识库前检查 `document_count`，含文档则 409 拒绝。
6. **用户隔离**：文档 list/get 按 `user_id` 过滤，跨用户 404（collection 按用户划分）。
7. **上传校验服务端强制**：格式 PDF/DOC/DOCX/TXT、大小上限（默认 20MB），非法 422。

## 测试策略

TDD：先写 `tests/test_document_service.py`（哈希/提取/切片/向量化/状态机/删除级联）与 `tests/test_knowledge_base_service.py`（CRUD/唯一名/删除检查），全红后实现，迭代至全绿；端点级 RBAC 与隔离另写 `tests/test_document_endpoints.py`、`tests/test_knowledge_base_endpoints.py`。
