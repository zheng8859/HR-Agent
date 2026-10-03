# Proposal

## Why

后端 JD 生成 / 评分标准 API（doc 36 Phase A）已就绪，但 `hragent-frontend` 仍是空 Vite 脚手架，招聘线核心用户流程（输入需求 → 流式生成 JD → 编辑确认 → 保存 → 生成评分标准 → 人工确认权重 → 保存）无法走通。需要落地两个前端页面，把「AI 出初稿、人定终稿」的受控自动化理念落到可操作界面。

## What Changes

- 搭建 Vue 应用壳层：Vue Router + Pinia + Element Plus 接线，axios 客户端（`/api/v1` baseURL + JWT 拦截器 + 401 跳登录），Vite dev proxy 到后端 `http://localhost:8000`。
- 新增主布局（侧边栏导航 + 顶栏），对应原型 `frontend/pages/` 的导航结构，本期只激活「JD 生成」「评分标准」两项。
- 新增最小登录页（复用 `/auth/login`）以获取 JWT，支撑前后端联调。
- 新增 **JD 生成页**：双入口（表单字段 / 一句话描述解析填充）、SSE 流式打字机展示、初稿可编辑、确认保存、已保存 JD 列表（draft/published/archived 状态标签）、删除二次确认、生成失败保留输入可重试。
- 新增 **评分标准页**：关联 JD、AI 生成维度（name/weight/max_score/description）、权重可编辑、总分实时合计、**不配平提示人工确认**（不自动修正）、保存并锁定、删除二次确认。

## Capabilities

### New Capabilities

- `jd-generator-ui`: JD 生成页前端交互能力——双入口输入、流式展示、编辑确认、已保存列表、删除二次确认。
- `scoring-criteria-ui`: 评分标准页前端交互能力——维度权重编辑、人工确认、绑定 JD、删除二次确认。

### Modified Capabilities

<!-- 无后端规格变更；认证/授权/JD 生成/评分标准规格已在 doc 36 Phase A 建立，前端仅作为其客户端，不改变 spec 级行为。 -->

## Impact

- 前端 `hragent-frontend/`：`src/main.js`、`src/router/`、`src/store/`、`src/api/`、`src/layouts/`、`src/views/`、`vite.config.js`（新增 proxy）。
- 后端无改动；仅依赖已归档的 `jd-generation` / `scoring-criteria` / `authentication` API。
- 联调依赖一个可登录的 HR 角色账号（本地种子数据），用于验证写操作权限真门与全流程联通。
