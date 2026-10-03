# Design

## Context

`hragent-frontend` 是空 Vite+Vue 脚手架（vue/vue-router/pinia/element-plus/echarts/axios 已在 package.json 但未接线）。后端 API 已就绪：`/api/v1/auth/login`（OAuth2 密码流）、`/me`、`/job-descriptions/*`（generate / generate-stream / parse / CRUD / status）、`/scoring-criteria/*`（generate / CRUD / status）。原型 `frontend/pages/jd-generator.html` 与 `scoring-criteria.html` 给出目标 UI 与交互（双栏输入+流式预览、维度权重编辑+合计校验）。

## Goals / Non-Goals

**Goals:**
- 用 Element Plus（doc 23「Element Plus 默认主题、保持克制」）还原两个页面的交互流，而非照搬原型的 Tailwind 样式。
- 建立可复用的前端基础设施（router/pinia/axios/布局），供 37/38 及后续文档沿用。

**Non-Goals:**
- 不实现原型中的演示数据（localStorage 种子、Toast 演示）——真实联调后端。
- 不实现系统管理/用户管理页面（doc 41）；侧边栏只渲染本期两个入口 + 占位项。
- 不改变后端任何 spec 级行为。

## Decisions

1. **SSE 用 `fetch` + ReadableStream 而非 EventSource**：生成接口是 POST（需 JSON 请求体），EventSource 仅支持 GET。前端用 fetch 流式读取 `text/event-stream`，按空行分帧解析 `event:` / `data:`；组件卸载或重试时用 `AbortController` 中断连接（对应「流式中断可重试」与资源清理）。
2. **axios 实例 + 拦截器**：单例 `src/api/http.js`，`baseURL: '/api/v1'`，请求拦截器从 localStorage 注入 `Authorization: Bearer <token>`，响应拦截器在 401 时清 token 并跳 `/login`。
3. **Vite dev proxy**：`vite.config.js` 配置 `server.proxy['/api'] → http://localhost:8000`（不 rewrite，后端路由即 `/api/v1/...`），规避 CORS 并透传 SSE。
4. **登录用 `application/x-www-form-urlencoded`**（`URLSearchParams`）对齐 FastAPI `OAuth2PasswordRequestForm`，token 存入 localStorage + Pinia auth store。
5. **页面状态用组件内 `ref/reactive`**：JD 列表与评分维度均为页面局部状态，不引入全局 store（除 auth 外），避免过度设计；跨页传递（JD→评分标准）用路由 query 携带 `job_description_id` 与标题。
6. **权重合计在前端实时计算**：评分标准页维护维度数组，`computed` 求和与后端 `is_balanced/score_sum/difference` 双保险；不配平时禁用「保存并锁定」并提示，**不自动修正**（呼应后端 `validate_balance` 语义）。

## Risks / Trade-offs

- [流式内容渲染闪烁 / 组件卸载后仍写状态] → 卸载时 `abort()` + `isMounted` 守卫，事件回调先判存活。
- [axios 401 拦截在登录接口自身 401 时造成死循环] → 拦截器排除 `/auth/login` 路径。
- [Vite 代理未启动后端时页面报错] → 登录页与列表加载统一错误提示「后端未连接」，/qa 与联调前先启动 uvicorn。
- [mock 模式下生成返回固定内容，UI 无法覆盖真实字段差异] → 页面字段映射以 Pydantic schema 为准（title/department/location/…），不依赖 mock 特有字段。
