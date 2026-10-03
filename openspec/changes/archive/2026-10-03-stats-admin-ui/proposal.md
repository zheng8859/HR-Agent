# Proposal

## Why

统计看板与系统管理后端（`stats-admin`）已落地：`GET /stats/dashboard|trend|activities`（HR 管理员角色可见）、`/users`、`/roles`（仅超管）。但前端「系统管理」菜单仍是禁用占位，也没有数据看板页，超管无法在界面上管理用户与角色，HR 负责人也无法查看招聘/对话统计。补齐前端即打通「统计看板 + 系统管理」的闭环。

## What Changes

- 新增数据看板页 `DashboardView`（Vue 3 + Element Plus + ECharts）：概览卡、招聘/对话统计、近 30 天趋势折线图、最近活动列表。
- 新增用户管理页 `UsersView`：用户列表 + 新建/编辑弹窗 + 删除（禁止删除自己，后端 400 提示）。
- 新增角色管理页 `RolesView`：角色列表 + 新建/编辑弹窗 + 删除（内置角色 409 提示）。
- 菜单权限过滤：启用「系统管理」子菜单（仅超管可见），新增「数据看板」入口（HR 管理员角色可见）。
- 新增 API 模块 `stats.js` / `users.js` / `roles.js`，纯逻辑抽离到 `utils/permission.js`、`utils/stats.js` 并用 `node:test` 覆盖。

## Capabilities

### New Capabilities

- `stats-admin-ui`: 数据看板、用户管理、角色管理页面的前端交互能力，以及按角色/超管的菜单可见性过滤与展示格式化纯逻辑。

### Modified Capabilities

<!-- 无：后端 stats-admin 能力无 spec 级变化 -->

## Impact

- `hragent-frontend/src/api/stats.js`、`users.js`、`roles.js`（新增）：对接后端三组端点。
- `hragent-frontend/src/views/DashboardView.vue`、`UsersView.vue`、`RolesView.vue`（新增）：页面组件。
- `hragent-frontend/src/utils/permission.js`、`stats.js`（新增）：菜单权限与展示格式化纯逻辑。
- `hragent-frontend/src/store/auth.js`（修改）：新增 `isSuperuser` / `isHrAdmin` getter。
- `hragent-frontend/src/router/index.js`（修改）：注册 `dashboard` / `users` / `roles` 路由。
- `hragent-frontend/src/layouts/MainLayout.vue`（修改）：启用系统管理子菜单 + 数据看板入口 + 权限过滤。
- `hragent-frontend/tests/permission.test.js`、`stats.test.js`（新增）：前端纯逻辑单测。
- 无后端改动。
