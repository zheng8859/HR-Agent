# Tasks

## 1. 配置与 Dify 客户端

- [ ] 1.1 `app/core/config.py` 新增 Dify 配置（base_url/api_key/JD 工作流/评分标准工作流/超时）与 `dify_configured` 属性。验证：未配置时 `dify_configured=False`。
- [ ] 1.2 `app/services/dify_service.py` 实现异步 `DifyClient`：`run_jd_workflow` / `run_scoring_workflow` / `stream_jd_workflow`，无密钥时返回确定性 mock。验证：mock 模式返回结构正确的 JD/评分标准。

## 2. Schema

- [ ] 2.1 `app/schemas/job_description.py`：JD 创建/更新/响应/生成输入/解析结果 schema（title/content 必填，skills/requirements 列表）。验证：schema 校验通过。
- [ ] 2.2 `app/schemas/scoring_criteria.py`：评分标准创建/更新/响应/生成结果 schema（维度 name/weight/max_score/description，total_score 默认 100，balance 标志）。验证：默认总分 100、维度结构校验。
- [ ] 2.3 `app/schemas/auth.py`：登录请求/Token 响应 schema。

## 3. 服务

- [ ] 3.1 `app/services/job_description_service.py`：`parse_requirement`（一句话→结构化字段）+ `generate_jd`（表单直生）+ `generate_jd_stream`（SSE 事件）+ CRUD + 状态机。验证：双入口/解析/必填/SSE 事件序列/状态守卫。
- [ ] 3.2 `app/services/scoring_criteria_service.py`：`generate_scoring_criteria` + `validate_balance`（不配平标志、不自动修正）+ CRUD + 绑定 JD 存在性校验。验证：维度结构/总分默认 100/权重确认/绑定。

## 4. 端点与路由

- [ ] 4.1 `app/api/v1/endpoints/job_descriptions.py`：list/get/create/update/delete/generate/generate-stream/parse/change-status，写操作 `get_current_admin_by_role`。验证：权限拒绝/CRUD/流式。
- [ ] 4.2 `app/api/v1/endpoints/scoring_criteria.py`：list/get/create/update/delete/generate，写操作鉴权。验证：权限/CRUD/绑定/权重确认。
- [ ] 4.3 `app/api/v1/endpoints/auth.py`：`/auth/login` + `/auth/me`。验证：登录签发、当前用户。
- [ ] 4.4 `app/api/v1/api.py` 聚合路由 + `app/main.py` 挂载。验证：应用可启动、路由可访问。

## 5. 集成校验

- [ ] 5.1 全量单元测试回归 + JD/评分标准新测试全绿。
