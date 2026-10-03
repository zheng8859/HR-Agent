# Proposal

## Why

文档处理与知识库后端（`doc-kb`）已落地：文档上传哈希、文本提取、语义切片、向量化、状态机、知识库 CRUD、删除级联均已可用。但前端缺少知识库管理页，HR 无法新建知识库、上传文档、查看处理状态与切片、删除与失败重试。补齐该页面即打通「文档入库 → 知识问答」的前置环节。

## What Changes

- 新增知识库管理前端页面 `KnowledgeManagementView`（Vue 3 + Element Plus），参考原型 `frontend/pages/knowledge-management.html` 还原设计。
- 知识库列表与新建（名称必填、公开/可搜索开关）、编辑、删除（含文档则后端 409，前端提示）。
- 文档上传（选择知识库 + 文件），上传后展示处理状态（已上传/处理中/已处理/失败）并自动轮询刷新，全部终态后停止。
- 查看切片抽屉/弹窗；删除文档二次确认；处理失败可「重新处理」。
- 空态：无知识库 / 无文档均有引导。

## Capabilities

### New Capabilities

- `knowledge-management-ui`: 知识库管理页的前端交互能力（知识库 CRUD、文档上传与状态轮询、查看切片、删除确认、失败重试、空态）。

### Modified Capabilities

<!-- 无：后端 doc-kb 能力无 spec 级变化 -->

## Impact

- `hragent-frontend/src/api/knowledgeBase.js`（新增）：对接 `/knowledge-base` 端点。
- `hragent-frontend/src/api/document.js`（新增）：对接 `/documents` 端点。
- `hragent-frontend/src/views/KnowledgeManagementView.vue`（新增）：页面组件。
- `hragent-frontend/src/utils/document.js`（新增）：状态元数据、文件大小/时间格式化纯逻辑。
- `hragent-frontend/src/router/index.js`（修改）：注册 `knowledge` 路由。
- `hragent-frontend/src/layouts/MainLayout.vue`（修改）：启用「知识助理 · 知识库管理」菜单项。
- `hragent-frontend/tests/document.test.js`（新增）：前端纯逻辑单测。
- 无后端改动。
