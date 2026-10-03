# Design — Evals 评测体系

## 背景

评测分两个互补视角（00 §三 / 19 号文档）：TDD 管「系统正确性」（pytest 单元/集成），Evals 管「AI 输出质量」（Golden 测试集 + 规则检查 + LLM 裁判）。本变更只做后者，二者不可互相替代。

## 目标与非目标

- **目标**：像对待普通软件一样对待 AI 质量——用测试度量、用基线对比、用 CI 守护。
- **非目标**：不实现 Agent 编排（43/44）；不替人改分（分值配平只报告不修正）；不调整业务阈值。

## 决策

### D1：L1/L2 对 Agent 契约的「参考规则」落在评测包

文档 42 的 L1 目标（意图关键词匹配/缺口分类/工具函数/SSE 构造）指向文档 43 才实现的 Agent 层（快慢双通道、ReAct、SSE 流式）。为让评测框架在 `v0.5.0` 可独立验收，本变更在评测包内提供**确定性参考规则**（编码 16 号 §二/§三/§7 契约：意图枚举、工具注册表、返回结构、SSE 事件结构），用于：(a) 校验 Golden 样本自洽；(b) L3 `agent_cases` 无真实 Agent 时以 mock 跑通框架。文档 43 落地时其 `_classify_agent_intent` 等实现须与此参考规则在 Golden 样本上行为一致——这正是 `agent_cases` 的回归意义。**不实现** Gateway/ReAct/SSE 端点/工具 handler。

### D2：三层粒度金字塔

| 层 | 对象 | 通过标准 | 运行 |
|----|------|:------:|------|
| L1 | 纯函数/规则（eval_utils + 参考规则 + 既有 validate_balance/状态机） | ≥95% | <5s，无外部依赖 |
| L2 | API 端点行为（招聘/知识/系统管理）+ SSE 事件构造 | ≥90% | 需 DB |
| L3 | AI 输出质量（agent/dify/rag 三套） | ≥85% | 慢，真实 LLM / mock |

L1 30 道 = 意图匹配 8 + 缺口分类 6 + 状态机 8 + 评分求和 4 + 工具函数 4。
L2 24 道 = 招聘端点 8 + 知识端点 6 + 系统管理端点 5 + SSE 契约 5。

### D3：L3 三套测试集阈值（红线，按错误类型差异化）

`agent_cases` ≥90%（规则 + LLM 裁判）；`dify_cases` ≥75%（结构/分值规则 + LLM）；`rag_cases` ≥70%（检索/生成分测）。三套阈值与 L3 整体 ≥85%（按样本量 50/40/30 加权）**同时生效**：子类允许宽松，整层不得跌破 85%。

### D4：容差参数（单一事实来源，见 spec）

`intent_match/route_match/contract_fields="exact"`、`structure_completeness_min=0.9`、`score_sum_equals_total=true`、`required_keywords_ratio=0.7`、`retrieval_recall_min=0.8`、`citation_accuracy_min=0.8`、`faithfulness_min=0.8`、`confidence_range=±0.15`、`response_time_max_seconds=30`。

### D5：边界条件独立监控（不能套通用阈值）

1. 意图误判（`category=ambiguous`）子类意图准确率 ≥85%，单独输出防被平均掩盖。
2. 分值配平由规则检查 100% 通过，只报告不修正。
3. RAG 无依据拒答（`should_refuse=true`）≥90%，独立统计。
4. 高风险确认（`category=risky`）`requires_confirmation=true` 100%（规则）。
5. SSE 事件序列完整性 100%（L2 契约）。

### D6：数据模型

`golden_samples`：`id`(str 唯一)、`suite`(agent/dify/rag)、`category`、`payload`(JSONB 原始样本)、`tags`(JSONB)、`created_at`。
`eval_runs`：`id`、`suite`、`tier`、`total`、`passed`、`pass_rate`、`metrics`(JSONB)、`is_baseline`、`created_at`。

### D7：回归基线

`golden_agent_007`(自然语言简历筛选≥90%)、`golden_agent_021`(删除低分候选人确认 100%)、`golden_dify_012`(分值配平 100%)、`golden_dify_003`(JD 章节完整≥90%)、`golden_dify_024`(面试方案绑定评估≥90%)、`golden_rag_005`(未收录制度拒答≥90%)。基线上调须业务复核；下调禁止。

### D8：劣化决策树

≤3% 正常；3-5% 记 devlog；>5% PR 自动评论告警；>10% 建议阻断（人工判断）。

## 风险与权衡

- **LLM 随机性** → 重复运行 + 置信度 ±15% 容差 + 基线对比而非绝对值。
- **Golden 样本维护成本** → 测试集是活资产，每次踩坑补样本；回归清单防再犯。
- **mock 与真实的差距** → L3 有 key 时跑真实 Qwen，无 key 时 mock 只验证框架管线，CI 只跑 L1/L2。
- **Agent 契约前向引用** → 由 D1 化解：参考规则只编码契约、不实现编排，43 落地即对齐。
