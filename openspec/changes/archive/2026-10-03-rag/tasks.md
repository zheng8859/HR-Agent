# Tasks

## 1. 配置与基础设施

- [ ] 1.1 `app/core/config.py` 新增 LLM（base_url/api_key/model）、Rerank（base_url/api_key/model/top_k）、RAG 检索参数（top_k/source_chunks/权重）与 `llm_configured`/`rerank_configured`。验证：默认值正确。
- [ ] 1.2 `app/services/embedding_service.py`：新增 `tokenize_text`，`_mock_embed` 改为词面 bag-of-words（feature hashing + L2 归一化）。验证：维度 1536、确定性、词面重叠越高余弦越高。

## 2. 服务

- [ ] 2.1 `app/services/llm_service.py`：`classify_kb` / `rewrite_query`（≤6 关键词）/ `generate_answer`（mock + 真实 API 钩子）。验证：分类/改写/生成确定性。
- [ ] 2.2 `app/services/rerank_service.py`：`rerank` + `rerank_or_fallback`（失败降级原始排序）。验证：异常回退不中断。
- [ ] 2.3 `app/services/kb_selection_service.py`：`is_chitchat`（闲聊预筛）+ `should_use_kb`（LLM 分类）。验证：闲聊不走库、制度类走库。
- [ ] 2.4 `app/services/rag_service.py`：`cosine_similarity` / `vector_score` / `text_score` / 检索打分合并（0.7/0.3）/ 阈值过滤 / 来源片段 / `ask` 编排。验证：检索排序、阈值、拒答、来源。

## 3. Schema 与端点

- [ ] 3.1 `app/schemas/knowledge_assistant.py`：请求/响应（含 `document_chunks` 结构）。验证：校验通过。
- [ ] 3.2 `app/api/v1/endpoints/knowledge_assistant.py`：`POST /ask`（`get_current_user`）。验证：闲聊/有依据/无依据三态返回正确。
- [ ] 3.3 `app/api/v1/api.py` 注册 `/knowledge-assistant` 路由。验证：可访问。

## 4. 测试

- [ ] 4.1 `tests/test_llm_service.py`：分类 KB/GENERAL、改写 ≤6、生成带来源。
- [ ] 4.2 `tests/test_rerank_service.py`：降级回退原始排序。
- [ ] 4.3 `tests/test_kb_selection_service.py`：闲聊预筛边界。
- [ ] 4.4 `tests/test_rag_service.py`：余弦、0.7/0.3 合并、阈值过滤、检索排序、拒答、来源片段。
- [ ] 4.5 `tests/test_knowledge_assistant_endpoints.py`：RBAC、三态、用户隔离。
