# Proposal

## Why

招聘四环节（36-38）、知识助理（39-40）与系统管理（41）已把「系统对不对」交给 pytest 单元/集成测试覆盖，但「AI 输出好不好」——意图识别准不准、生成内容完不完整、RAG 回答忠不忠实——仍是「凭感觉」。招聘与知识问答直接面向真实候选人与员工，AI 误判意图、评分不配平、无依据硬答都会产生业务后果。本变更为项目搭建评测体系：用 Golden 测试集度量、用基线对比劣化、用 CI 门禁守护，让每次改动都能回答「AI 变好了还是变差了」。

## What Changes

- **三套 Golden 测试集（120 样本 + 1 Schema）**：`agent_cases`（50，意图/工具/契约/确认）、`dify_cases`（40，JD/评分/简历/面试生成质量）、`rag_cases`（30，检索 + 生成/拒答）。JSON 文件 + `schema.json` 总 Schema。
- **评测工具函数（`eval_utils.py`）**：结构完整性、分值配平、关键词覆盖、语义相似度、检索指标（recall/hit/rank）、生成指标（faithfulness/relevance/citation）、意图/路由/契约精确匹配、工具注册表校验、SSE 事件构造、聚合指标。全部纯函数、确定性。
- **三评测器**：`agent_eval`（意图/契约/确认判定）、`dify_eval`（结构/分值/关键词）、`rag_eval`（检索 + 生成分测）。L3 依赖真实 LLM（Qwen），无 key 时 mock 跑通框架。
- **数据存储**：`golden_samples` + `eval_runs` 表，`seed_evals.py` 导入 JSON 便于程序化查询与报告。
- **CLI 运行器（`run_evals.py`）**：`--tier l1|l2|l3|all`、`--suite`、`--run-slow`、`--compare baseline.json`、`--save-baseline`、`--output html`、`--json`。
- **三层测试框架**：L1 单元（≥95%）/ L2 集成（≥90%）/ L3 质量（≥85%），pytest 标记 `l1/l2/l3/slow`，`evals/conftest.py` 共享夹具。
- **CI 门禁**：`.github/workflows/evals-ci.yml` —— L1 阻断 + L2/L3 劣化告警。
- **回归基线**：`golden_agent_007/021`、`golden_dify_003/012/024`、`golden_rag_005` 六样本 + 维护规则 + 劣化决策树。

## Capabilities

### New Capabilities

- `evals`: 三套 Golden 测试集、评测工具函数、三评测器、三层测试框架、CLI 运行器、基线对比、CI 门禁。

### Modified Capabilities

<!-- 无 -->

## Impact

- `hragent-backend/app/evaluations/eval_utils.py`（新增）：纯函数工具集。
- `hragent-backend/app/evaluations/base.py`、`agent_eval.py`、`dify_eval.py`、`rag_eval.py`（填充）：三评测器 + 基类。
- `hragent-backend/app/models/eval.py`（新增）：`GoldenSample` / `EvalRun` 模型。
- `hragent-backend/evals/schema.json` + `evals/{agent,dify,rag}_cases/*.json`（新增）：120 样本 + Schema。
- `hragent-backend/evals/conftest.py`（新增）：DB / Golden 加载 / API client / 认证 token。
- `hragent-backend/scripts/seed_evals.py`、`scripts/run_evals.py`（新增）：种子导入 + CLI 运行器。
- `hragent-backend/tests/test_l1_unit_*.py`、`test_l2_integration_*.py`、`test_l3_quality_*.py`（新增）：三层测试。
- `hragent-backend/pytest.ini`（修改）：`l1/l2/l3/slow` 标记 + pytest-json-report。
- `.github/workflows/evals-ci.yml`（新增）：L1 阻断 + L2/L3 劣化告警。
- 无前端改动。

## Out of Scope

- Agent 编排层实现（`intent_service.py` 快慢双通道、ReAct、SSE 流式端点、工具 handler）—— 属文档 43/44，本变更仅编码其契约（意图枚举/工具注册表/返回结构）供评测对比。
- 真实 LLM 评测的密钥配置（有 key 才跑 L3 真实语义，否则 mock）。
- 邮件通知 / 试卷生成（本期范围外，`email_notification` / `exam_generate` 仅在工具注册表中留边界）。
