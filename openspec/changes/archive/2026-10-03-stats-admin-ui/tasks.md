# Tasks

## 1. 纯逻辑与 API

- [ ] 1.1 `src/utils/permission.js`：`HR_ADMIN_ROLES`、`isHrAdmin`、`isSuperuser`。验证：角色/超管判定正确。
- [ ] 1.2 `src/utils/stats.js`：`ROLE_LABELS`、`roleLabel`、`formatGrowth`。验证：标签映射与环比格式化正确。
- [ ] 1.3 `src/api/stats.js`、`users.js`、`roles.js`：对接三组端点。验证：路径与方法正确。

## 2. 页面与路由

- [ ] 2.1 `src/views/DashboardView.vue`：概览卡、招聘/对话统计、趋势折线图、最近活动。验证：交互完整。
- [ ] 2.2 `src/views/UsersView.vue`：列表 + 新建/编辑/删除。验证：CRUD 完整，密码不回显。
- [ ] 2.3 `src/views/RolesView.vue`：列表 + 新建/编辑/删除，内置角色保护。验证：内置角色删除被拦截提示。
- [ ] 2.4 `src/router/index.js` 注册 `dashboard` / `users` / `roles` 路由。验证：可访问。
- [ ] 2.5 `src/store/auth.js` 新增 `isSuperuser` / `isHrAdmin` getter。验证：依据 user 计算。
- [ ] 2.6 `src/layouts/MainLayout.vue` 启用系统管理子菜单 + 数据看板入口 + 权限过滤。验证：按角色/超管显隐。

## 3. 测试

- [ ] 3.1 `tests/permission.test.js`：`isHrAdmin` / `isSuperuser` 边界。验证：全部通过。
- [ ] 3.2 `tests/stats.test.js`：`roleLabel` / `formatGrowth` 边界。验证：全部通过。
