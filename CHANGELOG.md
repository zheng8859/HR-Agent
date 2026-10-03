# Changelog

本文件记录 HR Agent 项目的全部发布说明，按 [Conventional Commits](https://www.conventionalcommits.org/) 规范分组。

---

## [v1.0.0] - 2026-10-03

> HR Agent 企业人力资源 AI 助手 —— 首个正式发布版本。涵盖四大模块：智能招聘（JD / 评分标准 / 简历评估 / 面试方案四环节闭环）、知识助理（文档处理 / RAG 问答）、Agent 对话入口（6 工具受控编排 + SSE 流式）、系统管理（用户 / 角色）。核心理念「受控自动化」：AI 出初稿、人定终稿。

### 版本里程碑

| 版本 | 阶段 | 说明 |
|------|------|------|
| v0.1.0 | 环境搭建 | 项目骨架 + Docker Compose |
| v0.2.0 | 数据模型 + 认证 | 10 本地模型 + JWT + 4 角色 RBAC |
| v0.3.0 | 招聘 | JD / 评分标准 / 简历评估 / 面试方案 |
| v0.4.0 | 知识 + 系统管理 | 文档处理 / 知识库 / RAG / 看板 / 用户角色 |
| v0.5.0 | Evals | 三层质量体系（L1/L2/L3）+ 基线对比 |
| v0.6.0 | Agent | 意图双通道 + 6 工具 + 对话前端 |
| v1.0.0 | 发布 | 验收 + 灰度发布 + 复盘 |

### 质量门禁

- 后端测试：**311 passed**（pytest）
- 前端测试：**44 passed**（node:test）
- Evals：L1 66/66 · L2 31/31 · L3 120/120（agent 50 / dify 40 / rag 30），对比 baseline 无劣化
- 安全审计：**A 级**（无 Critical / High）

---

### ✨ 新功能（feat）

#### 招聘四环节
- [891c9b9](https://github.com/zheng8859/HR-Agent/commit/891c9b9) JD 生成服务（双入口/解析/SSE 流式）+ CRUD + 状态机
- [6c1ab06](https://github.com/zheng8859/HR-Agent/commit/6c1ab06) 评分标准生成（维度权重/配平校验）+ CRUD + 绑定 JD
- [733a122](https://github.com/zheng8859/HR-Agent/commit/733a122) 简历评估后端（上传/文本提取/五维度评分/状态流转/导出）
- [32f982b](https://github.com/zheng8859/HR-Agent/commit/32f982b) 面试方案后端生成/编辑/导出闭环
- [69f579f](https://github.com/zheng8859/HR-Agent/commit/69f579f) 招聘四环节模型（JD/评分/简历/面试，外键闭环）

#### 知识助理
- [b4ecb96](https://github.com/zheng8859/HR-Agent/commit/b4ecb96) 文档处理管线（哈希/提取/切片/向量化/状态机/删除级联）
- [e493505](https://github.com/zheng8859/HR-Agent/commit/e493505) 知识库 CRUD 与路由注册
- [01b2215](https://github.com/zheng8859/HR-Agent/commit/01b2215) RAG 问答管线（走库判断/改写/多路径检索/重排/生成/拒答）
- [5dac902](https://github.com/zheng8859/HR-Agent/commit/5dac902) KnowledgeBase/Document 知识模型（embedding Vector 1536）

#### Agent 对话
- [144b2aa](https://github.com/zheng8859/HR-Agent/commit/144b2aa) Agent 编排核心（意图分类/决策/工具注册表/SSE/审计）
- [1668faa](https://github.com/zheng8859/HR-Agent/commit/1668faa) 6 工具真实 handler + ToolOutcome 异步编排 + 删除两步确认
- [406db2e](https://github.com/zheng8859/HR-Agent/commit/406db2e) 对话前端 HRAgentView + SSE 客户端 + 路由/菜单入口
- [55b4154](https://github.com/zheng8859/HR-Agent/commit/55b4154) Conversation/Message 对话模型（含回复树）

#### 系统管理与统计
- [9620e97](https://github.com/zheng8859/HR-Agent/commit/9620e97) 用户管理 + 角色管理服务与端点（仅超管，内置角色保护）
- [fdfafaf](https://github.com/zheng8859/HR-Agent/commit/fdfafaf) 统计看板聚合服务与端点（概览/趋势/最近活动）
- [975ed63](https://github.com/zheng8859/HR-Agent/commit/975ed63) User/Role 身份模型 + user_role 多对多

#### 认证与基础设施
- [51b3e74](https://github.com/zheng8859/HR-Agent/commit/51b3e74) JWT + bcrypt + RBAC 依赖注入
- [f10a0eb](https://github.com/zheng8859/HR-Agent/commit/f10a0eb) /auth/login + /auth/me 补齐认证链末端
- [e799604](https://github.com/zheng8859/HR-Agent/commit/e799604) Dify 客户端（type=1/2 工作流，未配置走 mock）
- [f4e326f](https://github.com/zheng8859/HR-Agent/commit/f4e326f) 异步 Alembic 初始化迁移
- [031b7e5](https://github.com/zheng8859/HR-Agent/commit/031b7e5) Base 基类 + 状态枚举 + 异步引擎与配置

#### 评测体系
- [210800e](https://github.com/zheng8859/HR-Agent/commit/210800e) 评测纯函数与三套评测器
- [dd6cf2c](https://github.com/zheng8859/HR-Agent/commit/dd6cf2c) Golden 样本持久化模型与评测种子
- [a8689db](https://github.com/zheng8859/HR-Agent/commit/a8689db) 120 条 Golden 测试集与 schema.json
- [4164ffe](https://github.com/zheng8859/HR-Agent/commit/4164ffe) seed_evals 与 run_evals CLI

#### 前端页面
- [a990415](https://github.com/zheng8859/HR-Agent/commit/a990415) 应用壳层（router/pinia/element-plus/axios 接线 + 登录 + 主布局）
- [ac5f39c](https://github.com/zheng8859/HR-Agent/commit/ac5f39c) JD 生成页（双入口/流式/编辑确认/已保存列表）
- [ca8f597](https://github.com/zheng8859/HR-Agent/commit/ca8f597) 评分标准页（维度权重编辑/人工确认/绑定 JD）
- [0ccd54b](https://github.com/zheng8859/HR-Agent/commit/0ccd54b) 简历筛选页（上传/评估/评分卡/状态流转/导出）
- [b96f82d](https://github.com/zheng8859/HR-Agent/commit/b96f82d) 智能面试前端页面
- [49287c5](https://github.com/zheng8859/HR-Agent/commit/49287c5) 知识库管理页（知识库 CRUD + 文档上传/状态轮询/切片/删除确认）
- [a3aa5b4](https://github.com/zheng8859/HR-Agent/commit/a3aa5b4) 知识问答页（提问/来源片段/三态/重新生成）
- [1258e7d](https://github.com/zheng8859/HR-Agent/commit/1258e7d) 数据看板/用户/角色页面与菜单权限过滤
- [2558988](https://github.com/zheng8859/HR-Agent/commit/2558988) 系统管理 API 模块与权限/格式化纯逻辑
- [08bc2eb](https://github.com/zheng8859/HR-Agent/commit/08bc2eb) 聚合路由挂载（/api/v1 前缀）

### 🐛 缺陷修复（fix）

- [8c472c3](https://github.com/zheng8859/HR-Agent/commit/8c472c3) 删除有依赖的资源时拒绝并说明，避免外键冲突中断 SSE
- [4e5822f](https://github.com/zheng8859/HR-Agent/commit/4e5822f) 高风险确认改由 TOOL_SPECS 唯一真源派生 + 反馈限定 assistant
- [611f5f1](https://github.com/zheng8859/HR-Agent/commit/611f5f1) 补传 JD/评分标准生成输入，修正 .env.example 变量名
- [431b40e](https://github.com/zheng8859/HR-Agent/commit/431b40e) update/change_status 后 refresh 避免 MissingGreenlet
- [fcd94b5](https://github.com/zheng8859/HR-Agent/commit/fcd94b5) mock 检索改用词面覆盖率，避免长文档余弦稀释被阈值误杀
- [602152b](https://github.com/zheng8859/HR-Agent/commit/602152b) vite 代理目标改用 127.0.0.1，避免 localhost 解析到 IPv6 打到 Docker 容器
- [29f0586](https://github.com/zheng8859/HR-Agent/commit/29f0586) get_db 请求提交/异常回滚，修复 CRUD 写入不落库
- [242c2ed](https://github.com/zheng8859/HR-Agent/commit/242c2ed) SSE 流式错误兜底（error 事件 + 测试）

### ♻️ 重构（refactor）

- [dc32596](https://github.com/zheng8859/HR-Agent/commit/dc32596) 面试方案简化为三要素（目标/流程/题目≥5）
- [b57c673](https://github.com/zheng8859/HR-Agent/commit/b57c673) 聊天助手应用走 /v1/chat-messages，answer 按 JSON/markdown 解析
- [6cca97a](https://github.com/zheng8859/HR-Agent/commit/6cca97a) 方案 A 单应用单 key，type 分支 + 移除未用 workflow_id

### 🧪 测试（test）

- [1784764](https://github.com/zheng8859/HR-Agent/commit/1784764) JD/评分标准/认证 61 个测试 + 端点级 client 夹具
- [d2822bc](https://github.com/zheng8859/HR-Agent/commit/d2822bc) 28 个单元测试与异步夹具
- [e4d9c33](https://github.com/zheng8859/HR-Agent/commit/e4d9c33) 覆盖 4 角色 × 依赖注入权限矩阵
- [6440876](https://github.com/zheng8859/HR-Agent/commit/6440876) 前端纯逻辑单测（SSE 解析/权重配平/token 存取）
- [900af77](https://github.com/zheng8859/HR-Agent/commit/900af77) 简历评估服务与端点测试
- [a938f85](https://github.com/zheng8859/HR-Agent/commit/a938f85) 简历上传校验与进度百分比纯逻辑单测
- [bb10826](https://github.com/zheng8859/HR-Agent/commit/bb10826) 面试方案服务与端点测试
- [14e1352](https://github.com/zheng8859/HR-Agent/commit/14e1352) 面试方案分区解析纯逻辑单测
- [39b5f2a](https://github.com/zheng8859/HR-Agent/commit/39b5f2a) 文档处理服务与端点测试（哈希/切片/向量化/状态机/隔离）
- [7fd02b6](https://github.com/zheng8859/HR-Agent/commit/7fd02b6) 知识库服务与端点测试（CRUD/名称唯一/含文档删除 409）
- [c98515d](https://github.com/zheng8859/HR-Agent/commit/c98515d) 文档格式化纯逻辑单测（状态元数据/大小/时间/扩展名）
- [b1a8f88](https://github.com/zheng8859/HR-Agent/commit/b1a8f88) RAG 各环节与端点测试
- [f947e1f](https://github.com/zheng8859/HR-Agent/commit/f947e1f) 知识问答纯逻辑单测（拒答/低置信度/置信度格式化）
- [a32e85b](https://github.com/zheng8859/HR-Agent/commit/a32e85b) 权限判定与展示格式化纯逻辑单测
- [986f89d](https://github.com/zheng8859/HR-Agent/commit/986f89d) L1/L2/L3 评测测试与 pytest 标记

### 📚 文档（docs）

> 全部 `docs(openspec)` 提交遵循 OpenSpec 规格先行流程：`propose`（提案）→ `apply`（落地）→ `archive`（归档落库）。此处按模块归集关键归档，完整提案/归档历史见 `git log --oneline --grep=openspec`。

- [e9583cb](https://github.com/zheng8859/HR-Agent/commit/e9583cb) 归档 agent-tools 变更并落库 agent/agent-ui 规范（doc 44）
- [01bf47a](https://github.com/zheng8859/HR-Agent/commit/01bf47a) 归档 agent 变更并落库规范（doc 43）
- [52bf158](https://github.com/zheng8859/HR-Agent/commit/52bf158) 归档 evals 变更并落库规范
- [f977a42](https://github.com/zheng8859/HR-Agent/commit/f977a42) Evals 评测体系变更提案（三套 Golden + 三层框架 + 基线对比 + CI 门禁）
- [0101424](https://github.com/zheng8859/HR-Agent/commit/0101424) 归档 stats-admin-ui 变更并落库规范
- [c41d0d2](https://github.com/zheng8859/HR-Agent/commit/c41d0d2) 归档 stats-admin 变更并落库规范
- [34e1b1f](https://github.com/zheng8859/HR-Agent/commit/34e1b1f) 归档 knowledge-qa-ui 变更并落库规范
- [6e10dcd](https://github.com/zheng8859/HR-Agent/commit/6e10dcd) 归档 rag 变更并落库规范
- [cacc8d1](https://github.com/zheng8859/HR-Agent/commit/cacc8d1) 归档 knowledge-management 变更并落库规范
- [f50e645](https://github.com/zheng8859/HR-Agent/commit/f50e645) 归档 doc-kb 变更并落库规范
- [c81c44f](https://github.com/zheng8859/HR-Agent/commit/c81c44f) 归档面试方案变更
- [59a87f9](https://github.com/zheng8859/HR-Agent/commit/59a87f9) 归档 resume 变更，落地 resume-evaluation 规格
- [5aee6d4](https://github.com/zheng8859/HR-Agent/commit/5aee6d4) 归档 jd-scoring-frontend，生成 jd-generator-ui/scoring-criteria-ui 主规格
- [60138dc](https://github.com/zheng8859/HR-Agent/commit/60138dc) 追加数据模型与认证架构章节（v0.2.0）

### 🔧 杂项与工程（chore）

- [8d7bf7c](https://github.com/zheng8859/HR-Agent/commit/8d7bf7c) 版本号升至 1.0.0（后端 FastAPI version + 前端 package）
- [094830e](https://github.com/zheng8859/HR-Agent/commit/094830e) 生产化 Dockerfile + nginx + compose.prod + .env.production.example
- [9ffd759](https://github.com/zheng8859/HR-Agent/commit/9ffd759) 验收产物 for v1.0.0-rc.1（doc 45）
- [d284d2e](https://github.com/zheng8859/HR-Agent/commit/d284d2e) 版本号升至 0.5.0（阶段五收尾）
- [ce0a3ee](https://github.com/zheng8859/HR-Agent/commit/ce0a3ee) 评测基线 baseline.json 与报告产物忽略
- [6cb9d57](https://github.com/zheng8859/HR-Agent/commit/6cb9d57) 版本号升至 0.4.0（阶段四收尾）
- [3fb3a90](https://github.com/zheng8859/HR-Agent/commit/3fb3a90) 项目初始骨架

### 🚀 持续集成（ci）

- [7cbb531](https://github.com/zheng8859/HR-Agent/commit/7cbb531) GitHub Actions 评测门禁

---

## 历史版本

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0-rc.1 | 2026-10-03 | 全链路验收候选（11 页面 + API + 安全审计 A + Evals 全绿） |
| v0.6.0 | 2026-10-03 | Agent 编排核心 + 6 工具 + 对话前端 |
| v0.5.0 | 2026-10-03 | Evals 评测体系（L1/L2/L3 + 基线 + CI） |
| v0.4.0 | 2026-10-03 | 知识助理 + 系统管理 |
| v0.3.0 | 2026-10-03 | 招聘四环节闭环 |
| v0.2.0 | 2026-10-03 | 数据模型 + JWT + RBAC |
| v0.1.0 | 2026-10-03 | 环境搭建 + 项目骨架 |
