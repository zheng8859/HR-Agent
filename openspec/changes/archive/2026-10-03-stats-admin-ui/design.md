# Design

## 1. 页面结构

复用 Element Plus 既有风格（与 `KnowledgeManagementView` 一致），三页均「页头 + el-card + el-table」布局。

- **数据看板**：概览卡（岗位描述/简历评估/面试方案/对话，含环比增减）、招聘统计卡（简历评估总数/近 30 天/待处理面试/面试方案）、对话统计卡（会话总数/近 30 天）、近 30 天趋势折线图（ECharts）、最近活动列表。
- **用户管理**：`el-table` 列表 + 新建/编辑弹窗（用户名/邮箱/密码/姓名/手机号/部门/职位/员工编号/角色/是否启用）+ 删除（后端 400 提示「不能删除当前登录账号」）。
- **角色管理**：`el-table` 列表（内置角色打「内置」标签）+ 新建/编辑弹窗（名称/描述）+ 删除（后端 409 提示内置角色不可删除）。

## 2. 菜单权限过滤

- 「数据看板」入口：`HR_ADMIN_ROLES = ['admin','hr_manager','hr_specialist']`，`isHrAdmin(user)` 为真时可见。
- 「系统管理」子菜单（用户管理/角色管理）：`isSuperuser(user)` 为真时可见。
- 权限真门在后端（`get_current_admin_by_role` / `get_current_superuser`），前端隐藏只是体验优化；越权访问后端仍会 403。

## 3. 接口对接

三组端点均为普通 REST（非流式），前端用 axios + 按钮/表格 loading 表达加载态：

| 端点 | 用途 | 权限 |
|------|------|------|
| `GET /stats/dashboard` / `trend` / `activities` | 看板数据 | HR 管理员角色 |
| `GET/POST/PUT/DELETE /users` | 用户管理 | 仅超管 |
| `GET/POST/PUT/DELETE /roles` | 角色管理 | 仅超管 |

## 4. ECharts 趋势图

`trend` 返回 `{ days: [...], series: { jd/resume/interview/conversation: [...] } }`。用折线图渲染四条序列，x 轴为 `days`，`init` + `setOption` 于 `onMounted`，`onUnmounted` 调 `dispose` 防泄漏。

## 5. 纯逻辑抽离

- `utils/permission.js`：`HR_ADMIN_ROLES`、`isHrAdmin(user)`、`isSuperuser(user)`。
- `utils/stats.js`：`ROLE_LABELS`（4 角色中文名）、`roleLabel(role)`、`formatGrowth(growth)`（`null/undefined → '—'`，正数带 `+`，负数带 `-`，0 为 `0`）。

用 `node:test` 覆盖这两个纯逻辑模块，边界含缺失 user、未知角色、负环比。
