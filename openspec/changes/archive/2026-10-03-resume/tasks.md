# Tasks

## 1. 配置与 Dify 客户端

- [x] 1.1 `app/core/config.py` 新增 `dify_resume_workflow_id`（type=3）与上传限制（`resume_max_size_mb=10`、`resume_allowed_types=pdf,doc,docx`）。验证：默认值正确。
- [x] 1.2 `app/services/dify_service.py` 新增 `run_resume_workflow` + `MOCK_RESUME_OUTPUT`（五维度 score/max/reason，总分 100）。验证：mock 模式返回结构正确的评分。

## 2. Schema

- [x] 2.1 `app/schemas/resume_evaluation.py`：维度 `ResumeDimension(name/score/max/reason)`、生成请求/结果、创建、更新（状态）、响应、导出 schema。验证：schema 校验通过。

## 3. 服务

- [x] 3.1 `app/services/resume_evaluation_service.py`：`validate_upload`（格式/大小）+ `extract_text`（PDF/DOCX）+ `parse_dimensions`（五维度/总分=维度之和）+ `evaluate` + `evaluate_auto`（匹配 JD）+ CRUD + `update_status` + `export`，并按 `user_id` 过滤。验证：校验/提取/评分/状态/依赖/所有权。

## 4. 端点与路由

- [x] 4.1 `app/api/v1/endpoints/resume_evaluation.py`：`upload`（multipart）/`evaluate`/`evaluate-auto`/list/get/`PATCH status`/`export`，写操作 `get_current_admin_by_role`，读操作按 `user_id` 过滤。验证：权限拒绝/上传校验/评分/状态/导出/所有权。
- [x] 4.2 `app/api/v1/api.py` 聚合路由（如未注册则注册）。验证：应用可启动、路由可访问。

## 5. 测试

- [x] 5.1 `tests/test_resume_evaluation_service.py`：文件校验、文本提取、五维度解析、总分=维度之和、解析失败不评分、状态流转、导出。
- [x] 5.2 `tests/test_resume_endpoints.py`：RBAC（employee 写拒绝）、上传非法格式/超限、评估落库、数据依赖（缺 JD 拒绝）、所有权（仅见本人记录）。
