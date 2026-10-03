# Proposal

## Why

招聘四环节（36-38）与知识助理（39-40）已产生各业务域数据，但系统尚缺「统计看板」来回答「系统跑得怎么样」，也缺「用户/角色管理」来支撑账号与权限运营。本变更为阶段四补齐统计看板服务（概览卡/招聘/对话/趋势/最近活动）与系统管理后端（用户 CRUD、角色 CRUD），并贯彻「系统管理仅超管、权限真门在后端、内置角色删除保护」。

## What Changes

- **统计看板**：`GET /stats/dashboard`（概览卡 + 招聘统计 + 对话统计）、`GET /stats/trend`（近 30 天趋势）、`GET /stats/activities`（最近活动）。计数类指标含环比（近 30 天 vs 前 30 天），口径写清来源表与过滤条件。
- **用户管理**：`/users` CRUD（仅超管）。字段：用户名/邮箱/密码/姓名/手机号/部门/职位/员工编号/角色（4 枚举）/是否启用。密码 bcrypt 存储、响应不回传。
- **角色管理**：`/roles` CRUD（仅超管）。预置 4 内置角色（admin/hr_manager/hr_specialist/employee，`is_builtin=True`），内置角色禁止删除。
- **权限隔离**：系统管理端点统一 `get_current_superuser`；统计看板走 `get_current_admin_by_role`（admin/hr_manager/hr_specialist）。

## Capabilities

### New Capabilities

- `stats-admin`: 统计看板聚合、用户管理、角色管理、超管权限隔离、内置角色保护。

### Modified Capabilities

<!-- 无 -->

## Impact

- `hragent-backend/app/services/stats_service.py`（新增）：看板聚合/趋势/最近活动。
- `hragent-backend/app/services/user_service.py`（新增）：用户 CRUD + 密码哈希。
- `hragent-backend/app/services/role_service.py`（新增）：角色 CRUD + 内置角色预置 + 删除保护。
- `hragent-backend/app/schemas/stats.py`（新增）：看板响应 schema。
- `hragent-backend/app/schemas/user_management.py`（新增）：用户/角色请求与响应 schema。
- `hragent-backend/app/api/v1/endpoints/stats.py`（填充）：`/stats` 端点。
- `hragent-backend/app/api/v1/endpoints/users.py`（填充）：`/users` 端点 + `/roles` 端点（或独立 roles 文件）。
- `hragent-backend/app/api/v1/api.py`（修改）：注册 `/stats`、`/users`、`/roles`。
- `hragent-backend/app/main.py`（修改）：启动时预置 4 内置角色（lifespan）。
- `hragent-backend/tests/`（新增）：统计/用户/角色/权限测试。
- 无前端改动（前端在 Phase B 独立变更）。
