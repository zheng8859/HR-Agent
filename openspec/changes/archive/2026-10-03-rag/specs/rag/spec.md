# rag Specification

## Purpose
定义 RAG 知识问答后端能力：走库判断（闲聊预筛 + LLM 分类）、查询改写、多路径检索（向量 + tsvector 全文）加权合并、相似度阈值过滤、Rerank 重排与降级、LLM 生成答案与来源依据、无依据拒答、用户隔离。

## ADDED Requirements

### Requirement: 走库判断

系统 SHALL 采用两层策略判断是否走知识库：闲聊关键词预筛（你好/谢谢/你是谁）命中直接应答，否则 LLM 分类为 `KB` 或 `GENERAL`。

#### Scenario: 闲聊直接应答
- **WHEN** 用户输入纯问候（如「你好」「谢谢」）
- **THEN** 直接返回闲聊应答，不触发检索，intent 为 GENERAL

#### Scenario: 制度类走库
- **WHEN** 用户输入企业制度类问题（如「出差住宿标准是多少」）
- **THEN** LLM 分类为 KB，进入检索

### Requirement: 查询改写

系统 SHALL 调用 LLM 产出 `rewritten_query` 与 `expanded_keywords`（最多 6 个关键词）。

#### Scenario: 关键词不超过 6 个
- **WHEN** 查询改写问题
- **THEN** 返回 `rewritten_query` 与 ≤6 个 `expanded_keywords`

### Requirement: 多路径检索加权合并

系统 SHALL 同时使用向量召回与 PostgreSQL tsvector 全文检索，并按 `0.7 × 向量分 + 0.3 × 文本分` 加权合并。

#### Scenario: 加权系数
- **WHEN** 合并向量分与文本分
- **THEN** 合并分 = 0.7 × 向量分 + 0.3 × 文本分

#### Scenario: 全文检索参与
- **WHEN** 文档内容包含问题关键词
- **THEN** tsvector 全文检索命中并贡献文本分

### Requirement: 相似度阈值过滤

系统 SHALL 过滤合并分低于 `RAG_MIN_SIMILARITY_SCORE`（0.2）的结果。

#### Scenario: 低分过滤
- **WHEN** 某文档合并分 < 0.2
- **THEN** 该文档被过滤，不进入生成

### Requirement: Rerank 重排与降级

系统 SHALL 在启用时调用 Rerank（`gte-rerank-v2`）重排检索结果；Rerank 失败时降级为原始召回排序，不报错中断。

#### Scenario: 失败降级
- **WHEN** Rerank 调用失败
- **THEN** 回退为原始召回排序，接口不中断

### Requirement: 答案与来源

系统 SHALL 返回回答 + 来源片段（`document_chunks`）+ 置信度，回答仅依据检索片段。

#### Scenario: 返回来源可核对
- **WHEN** 有满足阈值的结果
- **THEN** 返回 answer、`document_chunks`（含文档名与片段）与 confidence

### Requirement: 无依据拒答

系统 SHALL 在无满足阈值的结果时返回「资料不足」，不生成确定性结论。

#### Scenario: 资料不足拒答
- **WHEN** 检索无满足阈值的结果
- **THEN** 返回资料不足提示，answered 为 false，不硬编答案

### Requirement: 用户隔离

系统 SHALL 保证检索范围限定当前用户（按 `user_id` 过滤），可按知识库过滤。

#### Scenario: 跨用户不可检索
- **WHEN** 用户提问
- **THEN** 仅检索其本人上传的文档
