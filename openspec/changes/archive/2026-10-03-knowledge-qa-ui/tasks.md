# Tasks

## 1. 纯逻辑与 API

- [ ] 1.1 `src/utils/qa.js`：`SUGGESTED_QUESTIONS`、`isRefusal`、`isLowConfidence`、`confidencePercent`。验证：拒答/低置信度/百分比判定正确。
- [ ] 1.2 `src/api/knowledgeAssistant.js`：`askQuestion(question, knowledgeBaseId)` → `POST /knowledge-assistant/ask`。验证：payload 正确（可选 knowledge_base_id）。

## 2. 页面与路由

- [ ] 2.1 `src/views/KnowledgeQaView.vue`：知识库域选择、消息流、三态展示、来源折叠、空态示例、重新生成、清空。验证：交互完整。
- [ ] 2.2 `src/router/index.js` 注册 `knowledge-qa` 路由。验证：可访问。
- [ ] 2.3 `src/layouts/MainLayout.vue` 启用「知识问答」菜单项。验证：导航可见。

## 3. 测试

- [ ] 3.1 `tests/qa.test.js`：`isRefusal` / `isLowConfidence` / `confidencePercent` 边界。验证：全部通过。
