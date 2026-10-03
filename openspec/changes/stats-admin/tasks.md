# Tasks

## 1. 服务

- [ ] 1.1 `app/services/stats_service.py`：`dashboard_stats` / `trend_data` / `recent_activities`。验证：各域计数、环比、近 30 天趋势、最近活动。
- [ ] 1.2 `app/services/user_service.py`：用户 list/create/get/update/delete + 密码哈希 + 删除自我保护。验证：字段完整、密码不回传。
- [ ] 1.3 `app/services/role_service.py`：`ensure_builtin_roles` + 角色 list/create/update/delete + 内置删除保护。验证：4 内置角色、删除保护。

## 2. Schema 与端点

- [ ] 2.1 `app/schemas/stats.py`：dashboard/trend/activities 响应。
- [ ] 2.2 `app/schemas/user_management.py`：用户/角色请求与响应（password 仅写、role 枚举校验）。
- [ ] 2.3 `app/api/v1/endpoints/stats.py`：`GET /stats/dashboard|trend|activities`（`get_current_admin_by_role`）。
- [ ] 2.4 `app/api/v1/endpoints/users.py`：`/users` CRUD（`get_current_superuser`）。
- [ ] 2.5 `app/api/v1/endpoints/users.py` 或独立文件：`/roles` CRUD（`get_current_superuser`）。
- [ ] 2.6 `app/api/v1/api.py` 注册 `/stats`、`/users`、`/roles`。
- [ ] 2.7 `app/main.py` lifespan 预置内置角色。

## 3. 测试

- [ ] 3.1 `tests/test_stats_service.py`：计数/环比/趋势/最近活动。
- [ ] 3.2 `tests/test_user_management_endpoints.py`：CRUD、密码不回传、角色枚举校验、删除自我保护。
- [ ] 3.3 `tests/test_role_management_endpoints.py`：内置角色、创建/删除保护。
- [ ] 3.4 `tests/test_system_admin_permissions.py`：非超管访问 /users、/roles、/stats 权限边界。
