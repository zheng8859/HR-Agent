# Tasks

## 1. 应用壳层与认证基础设施

- [x] 1.1 接线 Vue Router + Pinia + Element Plus 到 `main.js`，配置 Vite dev proxy（`/api` → `http://localhost:8000`），删除脚手架 HelloWorld，验证 `npm run build` 无报错
- [x] 1.2 新增 axios 客户端（`src/api/http.js`：`/api/v1` baseURL + Bearer 拦截器 + 401 跳登录，排除 `/auth/login`），验证单测覆盖 token 注入与 401 清理逻辑
- [x] 1.3 新增 Pinia auth store（token + user，localStorage 持久化）与登录页，验证 auth store 单测（登录成功存 token / 登出清空）通过
- [x] 1.4 新增主布局（侧边栏导航 + 顶栏），路由含 `/login`、`/jd-generator`、`/scoring-criteria` 与路由守卫，验证未登录访问受保护页跳转 `/login`

## 2. JD 生成页

- [x] 2.1 新增 SSE 解析工具 `src/utils/sse.js`（按空行分帧解析 `event:`/`data:`），验证单测覆盖 thinking/delta/final/error 事件与分块边界
- [x] 2.2 新增 JD 生成页 `views/JDGeneratorView.vue`（双入口表单 + 一句话解析回填 + 流式打字机 + 初稿编辑 + 确认保存 + 已保存列表状态标签 + 删除二次确认 + 失败保留输入重试），验证 `npm run build` 通过且 SSE/表单校验单测通过

## 3. 评分标准页

- [x] 3.1 新增权重合计工具 `src/utils/balance.js`（维度分值求和、与总分差值、是否配平），验证单测覆盖配平/不配平/空维度
- [x] 3.2 新增评分标准页 `views/ScoringCriteriaView.vue`（关联 JD + 维度权重编辑 + 实时合计 + 不配平禁用锁定并提示 + 保存锁定 + 删除二次确认），验证 `npm run build` 通过且配平计算单测通过

## 4. 前后端联调

- [x] 4.1 启动后端（uvicorn）与前端（vite dev），用种子 HR 账号登录后走通核心流程：输入需求 → 流式生成 JD → 编辑 → 保存 → 生成评分标准 → 确认权重 → 保存，验证无接口报错、产物正确落库
