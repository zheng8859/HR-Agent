# Proposal

## Why

阶段二（doc 35）已交付 10 个本地模型 + JWT 认证 + 4 角色 RBAC，但 `JobDescription` / `ScoringCriteria` 仍停留在「数据结构」层面：没有 JD 生成服务（Dify type=1 + SSE 流式 + 需求解析）、没有评分标准生成服务（Dify type=2 + 维度权重 + 绑定 JD），也没有对外 API 端点。本变更把招聘四环节的前两环「生成能力」落到后端——AI 出初稿、人定终稿，可编辑态落地。

## What Changes

- `app/core/config.py`：新增 Dify 配置（base_url / api_key / JD 工作流 / 评分标准工作流 / 超时），未配置时走 mock。
- `app/services/dify_service.py`：异步 Dify 客户端（httpx），统一封装 type=1/2 工作流的「调用 + 流式」两种形态，无密钥时降级 mock 输出。
- `app/schemas/job_description.py` / `app/schemas/scoring_criteria.py`：请求/响应 Pydantic schema（含维度 name/weight/max_score/description、总分默认 100）。
- `app/services/job_description_service.py`：JD 双入口生成（表单直生 / 一句话先解析）、SSE 流式、CRUD、状态机（draft/published/archived）、失败保留输入可重试。
- `app/services/scoring_criteria_service.py`：评分标准生成、维度权重校验（不配平提示人工确认、不自动掩盖）、CRUD、绑定 JD。
- `app/api/v1/endpoints/job_descriptions.py` / `scoring_criteria.py`：REST 端点（生成/流式生成/CRUD/状态变更），写操作走 `get_current_admin_by_role` 后端鉴权。
- `app/api/v1/api.py` + `app/main.py`：聚合路由并挂载。
- `app/api/v1/endpoints/auth.py` + `app/schemas/auth.py`：补齐 `/auth/login` / `/auth/me`（doc 35 遗留的认证链末端，招聘端点端到端鉴权所需）。
- 测试：JD 生成（双入口+解析+必填）、SSE 事件序列、JD CRUD/状态机、评分标准生成/权重确认/绑定。

**本期不建**：简历评估、面试方案（doc 37/38）；前端页面（Phase B，本变更仅后端）。

## Capabilities

### New Capabilities

- `jd-generation`: JD 生成与解析——双入口、需求解析、SSE 流式、CRUD 与状态机。
- `scoring-criteria`: 评分标准生成——维度结构、总分默认 100、权重人工确认、绑定 JD。

### Modified Capabilities

- `authentication`: 新增 `/auth/login`（OAuth2 密码流签发 JWT）与 `/auth/me`（当前用户）端点，补齐认证链末端。

## Impact

- 代码：`app/core/config.py`、`app/services/dify_service.py`、`app/services/job_description_service.py`、`app/services/scoring_criteria_service.py`、`app/schemas/{job_description,scoring_criteria,auth}.py`、`app/api/v1/{api.py,endpoints/*}`、`app/main.py`。
- 依赖：新增 `httpx`（Dify 异步调用）；其余复用 doc 35 已声明的依赖。
- 数据库：无表结构变更（复用 doc 35 的 `job_descriptions` / `scoring_criteria`）。
- 无 BREAKING 变更（全部为新增服务/端点/配置）。
