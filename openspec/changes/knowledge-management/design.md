# Design

## 目标

新增知识库管理前端页，对接 `doc-kb` 后端能力，还原原型 `knowledge-management.html` 的核心交互：知识库 CRUD、文档上传与状态展示、查看切片、删除确认、失败重试、空态。

## 页面结构

| 区块 | 内容 |
|------|------|
| 页头 | 标题 + 副标题 + 「上传文档」「新建知识库」按钮 |
| 知识库选择卡 | 知识库列表（名称/描述/文档数/公开/可搜索开关），选中一个作为文档上传目标 |
| 文档表格 | 文件名、大小、处理状态、切片数、上传时间、操作（查看切片/重新处理/删除） |
| 空态 | 无知识库 → 引导新建；无文档 → 引导上传 |

## 关键决策

1. **知识库切换**：左侧/顶部 `el-select` 列知识库，选中后按 `knowledge_base_id` 拉取文档；「公开/可搜索」用 `el-switch`，切换即调 `PUT /knowledge-base/{id}`。
2. **上传**：`el-upload` 选择文件 + 当前知识库，走 `POST /documents/upload`（multipart：`file` + `knowledge_base_id` 表单字段），成功后刷新列表并进入轮询。
3. **状态轮询**：存在 `uploaded` / `processing` 状态的文档时，每 3 秒刷新列表；全部进入终态（`processed`/`failed`）或组件卸载时停止。由于后端同步处理，多数情况上传即终态，轮询仍保留以覆盖未来异步化。
4. **查看切片**：`GET /documents/{id}/chunks` 返回 `{chunks}`，弹窗展示（前端 `el-dialog` 列表）。
5. **删除确认**：删除文档/知识库用 `ElMessageBox.confirm` 二次确认；删知识库若后端返回 409（含文档），展示「请先删除其中的文档」。
6. **失败重试**：`failed` 状态文档展示「重新处理」按钮，调 `POST /documents/{id}/reprocess`；「重新上传」走上传入口。
7. **纯逻辑抽离**：状态元数据 `DOCUMENT_STATUS_META`、`formatFileSize`、`formatUploadTime`、`fileExtension` 放 `utils/document.js`，用 node:test 单测。
8. **空态与失败态**：无知识库 → 新建引导；无文档 → 上传引导；失败 → `ElMessage.error` 展示后端 detail。

## 测试策略

TDD：先写 `tests/document.test.js` 覆盖 `formatFileSize` / `formatUploadTime` / `fileExtension` / 状态元数据，全红后实现，迭代至全绿；页面交互以 `vite build` + `npm run test` + 前后端联调脚本验证。
