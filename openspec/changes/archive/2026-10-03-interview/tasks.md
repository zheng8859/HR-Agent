# Tasks

## 1. 配置与 Dify 客户端

- [x] 1.1 `app/core/config.py` 新增 `dify_interview_workflow_id`（type=4）。验证：默认值正确。
- [x] 1.2 `app/services/dify_service.py` 新增 `run_interview_workflow` + `MOCK_INTERVIEW_OUTPUT`（七要素）。验证：mock 返回七要素结构。

## 2. Schema 与服务

- [x] 2.1 `app/schemas/interview_plan.py`：生成请求（`resume_evaluation_id`）、更新（`content`/`candidate_name`）、响应、导出。验证：schema 校验通过。
- [x] 2.2 `app/services/interview_plan_service.py`：`format_plan`（七要素渲染 markdown）、`resolve_candidate`（四态纯函数）、`generate_plan`（守卫 + 生成 + 状态联动）、`regenerate_plan`、`list/get/update`（所有权）、`export_plan`（md/txt）。验证：守卫/四态/七要素/状态联动/导出/所有权。

## 3. 端点与路由

- [x] 3.1 `app/api/v1/endpoints/interview_plans.py`：`generate`/`regenerate`/list/get/`PUT`/`export`（文件响应 + BOM）。写操作 `get_current_admin_by_role`，读操作按 `user_id` 过滤。验证：权限拒绝/守卫/导出编码。
- [x] 3.2 `app/api/v1/api.py` 注册 `/interview-plans` 路由。验证：应用可启动、路由可访问。

## 4. 测试

- [x] 4.1 `tests/test_interview_plan_service.py`：守卫、四态、七要素、状态联动、导出、重新生成、所有权。
- [x] 4.2 `tests/test_interview_plans_endpoints.py`：RBAC（employee 写拒绝）、守卫、导出 BOM 编码。
