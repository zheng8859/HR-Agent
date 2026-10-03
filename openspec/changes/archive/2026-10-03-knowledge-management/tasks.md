# Tasks

## 1. API 与纯逻辑

- [x] 1.1 `src/api/knowledgeBase.js`：`createKB`/`listKBs`/`updateKB`/`deleteKB`。验证：对接 `/knowledge-base`。
- [x] 1.2 `src/api/document.js`：`uploadDocument`/`listDocuments`/`getDocumentChunks`/`reprocessDocument`/`deleteDocument`。验证：上传走 multipart、切片返回。
- [x] 1.3 `src/utils/document.js`：`DOCUMENT_STATUS_META` + `formatFileSize` + `formatUploadTime` + `fileExtension`。验证：格式化正确。

## 2. 页面组件

- [x] 2.1 `src/views/KnowledgeManagementView.vue`：知识库选择与新建、文档上传与状态轮询、查看切片、删除确认、失败重试、空态。验证：交互完整、空态引导。

## 3. 路由与菜单

- [x] 3.1 `src/router/index.js` 注册 `knowledge` 路由。验证：路由可访问。
- [x] 3.2 `src/layouts/MainLayout.vue` 启用「知识助理 · 知识库管理」菜单项。验证：菜单可点击。

## 4. 测试

- [x] 4.1 `tests/document.test.js`：`formatFileSize`/`formatUploadTime`/`fileExtension`/状态元数据。验证：全绿。
