# Design

## 目标

在 doc 39 已落地的 `Document`（单 `Vector(1536)` + `extracted_content`）之上，实现 RAG 问答管线：走库判断 → 查询改写 → 多路径检索 → 加权合并 → 阈值过滤 → Rerank → LLM 生成 + 来源，贯彻「先翻资料、再回答」与「无依据宁可拒答」。

## 端点

| 动作 | 端点 | 权限 |
|------|------|------|
| 知识问答 | `POST /knowledge-assistant/ask` | 读（`get_current_user`，任意登录用户） |

请求 `{ question, knowledge_base_id? }`；响应 `{ answer, answered, confidence, intent, rewritten_query, expanded_keywords, document_chunks }`。无会话持久化（Agent 对话属 doc 44）。

## 关键决策

1. **检索粒度为文档级（不新增切片表）**：`Document.embedding` 为单向量，来源片段 `document_chunks` 由命中文档的 `extracted_content` 现场 `chunk_text` 切片后、选与问题词面最相关的一段派生。与 CLAUDE.md §八（10 张表）、doc 17 §2.4（单 `Vector(1536)`）对齐；chunk 级存储留待后续阶段。
2. **mock Embedding 升级为词面 bag-of-words**：doc 39 的 hash 随机向量在离线态 cosine≈0（阈值失效），改为 `tokenize_text`（中文 bigram + ASCII 单词）经 feature hashing 到 1536 维 + L2 归一化；词面重叠越高余弦越高，离线检索可排序。真实 Embedding API 路径不变。
3. **多路径检索**：向量分 = 余弦相似度映射到 `[0,1]`（`(cos+1)/2`）；文本分 = PostgreSQL `to_tsvector('simple', extracted_content) @@ plainto_tsquery('simple', query)` 命中后 `ts_rank` 归一化到 `[0,1]`（未命中记 0）。合并 `0.7 × 向量分 + 0.3 × 文本分`。中文默认分词弱（本期先用默认，后续接中文分词），中文检索主要由向量路径承接。
4. **阈值过滤**：合并分 `< settings.rag_min_similarity_score`（默认 0.2）过滤；全过滤则走拒答分支。
5. **Rerank 降级**：`rerank_or_fallback` 包裹真实 Rerank 调用，任一异常回退原始召回排序（不报错中断）；mock 态保持原序仅截断 `top_k`。
6. **走库判断两层**：`is_chitchat`（归一化后对闲聊短语集合精确匹配）→ 不命中再 `llm_classify`（mock：命中「讲笑话/你会什么/天气」等 GENERAL 关键词→GENERAL，否则 KB）。闲聊返回固定应答，不检索。
7. **生成仅依据片段**：`generate_answer`（mock）把 `document_chunks` 的文档名 + 片段拼进模板回答，天然「仅依据检索片段」；真实路径交给 LLM 并携带同样的来源约束。
8. **隔离**：候选文档按 `user_id` 过滤（跨用户不可检索），可选按 `knowledge_base_id` 过滤。

## 测试策略

TDD：先写 `tests/test_llm_service.py`（分类/改写≤6/生成）、`tests/test_rerank_service.py`（降级回退）、`tests/test_kb_selection_service.py`（闲聊预筛）、`tests/test_rag_service.py`（余弦/合并 0.7·0.3/阈值/检索排序/拒答/来源片段）全红，再实现至全绿；端点级 RBAC 与隔离另写 `tests/test_knowledge_assistant_endpoints.py`。检索单测用固定向量与固定语料；Rerank 用降级路径验证。
