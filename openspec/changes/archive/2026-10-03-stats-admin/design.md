# Design

## 1. 统计看板

### 1.1 口径（计数类反映使用量，不臆造分母）

| 指标 | 来源表 | 口径 |
|------|--------|------|
| JD 生成数 | `job_descriptions` | count(*) |
| 简历评估数 | `resume_evaluations` | count(*) |
| 面试方案数 | `interview_plans` | count(*) |
| 会话总数 | `conversations` | count(*) |
| 待处理面试数 | `resume_evaluations` | count(status == 'interview') |
| 近期增长（各域） | 对应表 | count(created_at ∈ 近 30 天) |
| 环比 | 对应表 | 近 30 天 vs 前 30 天 的增减 |

### 1.2 端点

- `GET /stats/dashboard`：`{ overview: [{key,label,value,growth}], recruitment: {...}, conversation: {...} }`。growth 为环比（近 30 天 - 前 30 天），无分母时记 0。
- `GET /stats/trend?days=30`：近 N 天逐日计数，4 条序列（jd/resume/interview/conversation），缺日补 0。
- `GET /stats/activities?limit=10`：跨域最近记录，`{id,type,title,created_at}`，按 created_at 降序。

## 2. 用户管理

- 端点：`GET /users`（分页 + 搜索 + 角色过滤）、`POST /users`、`GET /users/{id}`、`PUT /users/{id}`、`DELETE /users/{id}`。
- 字段：username/email/password/full_name/phone/department/position/employee_id/role（4 枚举）/is_active。
- 密码：bcrypt 哈希；create 必填、update 可选；响应永不回传 `hashed_password`。
- 删除保护：不能删除当前登录用户（400）。
- 角色枚举校验：role ∈ {admin, hr_manager, hr_specialist, employee}。

## 3. 角色管理

- 端点：`GET /roles`、`POST /roles`、`PUT /roles/{id}`、`DELETE /roles/{id}`。
- 预置 4 内置角色（`is_builtin=True`）：admin/hr_manager/hr_specialist/employee，由 `ensure_builtin_roles` 幂等 upsert。
- 删除保护：`is_builtin` 角色删除返回 409。
- 自定义角色：name 唯一；is_builtin 恒为 False。

## 4. 权限

- 系统管理（/users、/roles）全部 `get_current_superuser`（is_superuser）。
- 统计看板（/stats）`get_current_admin_by_role`（admin/hr_manager/hr_specialist）。
- 权限真门在后端，前端菜单隐藏只是体验优化。

## 5. 内置角色预置

`main.py` 加 lifespan 启动时 `ensure_builtin_roles`；`list_roles` 服务内再做一次幂等 ensure（测试事务下也能保证 4 角色存在）。
