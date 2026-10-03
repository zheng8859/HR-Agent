# Proposal

## Why

文档处理与知识库（doc 39）已把企业制度、政策、流程文档切片向量化入 pgvector，但「知识助理」尚缺问答能力：员工无法基于企业自身文档提问并获得带来源依据的回答。本变更为知识助理补齐 RAG 问答管线——走库判断 → 查询改写 → 多路径检索（向量 + tsvector 全文）→ 加权合并 → Rerank 重排（可降级）→ LLM 生成答案与来源，并贯彻「无依据宁可拒答」。

## What Changes

- **走库判断**：闲聊关键词预筛（你好/谢谢/你是谁）→ LLM 分类 `KB / GENERAL`（两层策略，闲聊直接应答不走库）。
- **查询改写**：LLM 产出 `rewritten_query` + `expanded_keywords`（≤6 个）。
- **多路径检索**：向量召回（余弦相似度）+ PostgreSQL tsvector 全文检索（`to_tsvector`/`plainto_tsquery`/`ts_rank`），加权合并 `0.7 × 向量分 + 0.3 × 文本分`，低于 `RAG_MIN_SIMILARITY_SCORE=0.2` 的结果过滤。
- **重排与降级**：启用时调 Rerank（`gte-rerank-v2`）；Rerank 失败降级为原始召回排序，不中断。
- **答案 + 来源 + 置信度**：LLM 生成回答并附带来源片段（`document_chunks`）与置信度，回答仅依据检索片段。
- **无依据拒答**：无满足阈值的结果时返回「资料不足」，不生成确定性结论。
- **隔离**：检索范围限定当前用户（`user_id`），可按知识库过滤。

## Capabilities

### New Capabilities

- `rag`: RAG 知识问答后端能力（走库判断、查询改写、多路径检索加权、阈值过滤、Rerank 降级、答案与来源、无依据拒答、用户隔离）。

### Modified Capabilities

<!-- 无 -->

## Impact

- `hragent-backend/app/core/config.py`（修改）：新增 LLM（Qwen）/ Rerank（gte-rerank-v2）/ RAG 检索参数与 `llm_configured`/`rerank_configured`。
- `hragent-backend/app/services/embedding_service.py`（修改）：mock 向量升级为词面 bag-of-words（`tokenize_text` + feature hashing），使向量相似度在离线态可检索。
- `hragent-backend/app/services/llm_service.py`（新增）：走库分类 / 查询改写 / 答案生成（mock + 真实 API 钩子）。
- `hragent-backend/app/services/rerank_service.py`（新增）：重排 + 失败降级。
- `hragent-backend/app/services/kb_selection_service.py`（新增）：闲聊预筛 + 走库判断。
- `hragent-backend/app/services/rag_service.py`（新增）：检索打分/合并/阈值/来源片段/生成编排。
- `hragent-backend/app/schemas/knowledge_assistant.py`（新增）：问答请求/响应。
- `hragent-backend/app/api/v1/endpoints/knowledge_assistant.py`（新增）：`POST /knowledge-assistant/ask`。
- `hragent-backend/app/api/v1/api.py`（修改）：注册 `/knowledge-assistant` 路由。
- `hragent-backend/tests/`（新增）：RAG 各环节测试。
- 无前端改动（前端在 Phase B 独立变更）。
