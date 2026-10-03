# Tasks

## 1. Golden 测试集与 Schema

- [x] 1.1 `evals/schema.json`：三套样本的 JSON Schema（agent/dify/rag 三种 shape）。
- [x] 1.2 `evals/agent_cases/{common,ambiguous,risky}.json`：50 样本（20+15+15），含回归样本 golden_agent_007/021。
- [x] 1.3 `evals/dify_cases/{jd,scoring,resume,interview}.json`：40 样本（10×4），含 golden_dify_003/012/024。
- [x] 1.4 `evals/rag_cases/{retrieval,generation}.json`：30 样本（15+15），含 golden_rag_005。

## 2. 评测工具函数

- [x] 2.1 `app/evaluations/eval_utils.py`：结构/分值配平/关键词/语义相似度/检索指标/生成指标/聚合 + 意图/路由/契约/缺口/工具注册表/SSE 事件构造 + Golden 加载与校验。

## 3. 评测器

- [x] 3.1 `app/evaluations/base.py`：`EvalResult` + `BaseEvaluator`（mock/LLM 裁判挂点、结果聚合）。
- [x] 3.2 `app/evaluations/agent_eval.py`：`classify_intent_fast` 参考规则 + `AgentEvaluator`（意图/路由/契约/确认/缺口/工具边界）。
- [x] 3.3 `app/evaluations/dify_eval.py`：`DifyEvaluator`（结构完整性/分值配平/关键词覆盖，接 `dify_client` mock）。
- [x] 3.4 `app/evaluations/rag_eval.py`：`RagEvaluator`（检索 recall/hit/rank + 生成 faithfulness/relevance/citation，接 `rag_service`）。

## 4. 数据模型与种子

- [x] 4.1 `app/models/eval.py`：`GoldenSample` / `EvalRun`，注册进 `app/models/__init__.py`。
- [x] 4.2 `scripts/seed_evals.py`：导入 JSON → `golden_samples`。

## 5. 测试框架

- [x] 5.1 `evals/conftest.py`：DB 会话 / Golden 加载 / API client / 认证 token。
- [x] 5.2 `tests/test_l1_unit_eval_utils.py`：L1 30 道（意图 8 + 缺口 6 + 状态机 8 + 评分求和 4 + 工具 4）。
- [x] 5.3 `tests/test_l2_integration_endpoints.py`：L2 24 道（招聘 8 + 知识 6 + 系统管理 5 + SSE 契约 5）。
- [x] 5.4 `tests/test_l3_quality_suites.py`：L3 三套（agent/dify/rag，mock 跑通）。
- [x] 5.5 `pytest.ini`：`l1/l2/l3/slow` 标记 + pytest-json-report 配置。

## 6. CLI 与 CI

- [x] 6.1 `scripts/run_evals.py`：`--tier`/`--suite`/`--run-slow`/`--compare`/`--save-baseline`/`--output html`/`--json`。
- [x] 6.2 `.github/workflows/evals-ci.yml`：l1-gate（阻断）+ l2-l3-evals（劣化告警）。
- [x] 6.3 依赖补充 `pytest-json-report`。

## 7. 验证与基线

- [x] 7.1 `pytest tests/ -m "l1 or l2 or l3"` 全绿（L1≥95%/L2≥90%/L3≥85%）。
- [x] 7.2 `run_evals --tier all --run-slow --save-baseline` 建立 baseline.json。
- [x] 7.3 `run_evals --tier all --compare baseline.json` 输出劣化报告。
- [x] 7.4 回归样本 6 个 ID 单独校验通过。
