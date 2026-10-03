# Proposal

## Why

RAG 知识问答后端（`rag`）已落地：`POST /knowledge-assistant/ask` 返回回答 + 来源片段（`document_chunks`）+ 置信度，并在无依据时返回「资料不足」。但「知识助理」尚缺知识问答页，员工无法通过前端提问并查看带溯源依据的回答。补齐该页面即打通「上传文档 → 向量化 → 知识问答」的知识助理闭环。

## What Changes

- 新增知识问答前端页面 `KnowledgeQaView`（Vue 3 + Element Plus），参考原型 `frontend/pages/qa.html` 还原设计。
- 知识库域选择：下拉选择检索范围，`全部知识库` 表示不过滤。
- 问答交互：输入问题 → 发送 → 展示回答 + 来源片段（可展开核对）。
- 三态展示：有依据（回答 + 来源）、低置信度（警示提示）、资料不足（拒答，不显示确定性结论）。
- 空态示例问题引导：无对话时展示高频问题，点击回填输入框。
- 重新生成：重发最后一条用户提问；清空对话独立入口。

## Capabilities

### New Capabilities

- `knowledge-qa-ui`: 知识问答页的前端交互能力（提问与回答展示、来源片段展开、低置信度/资料不足三态、空态示例问题、重新生成、知识库域选择）。

### Modified Capabilities

<!-- 无：后端 rag 能力无 spec 级变化 -->

## Impact

- `hragent-frontend/src/api/knowledgeAssistant.js`（新增）：对接 `POST /knowledge-assistant/ask`。
- `hragent-frontend/src/views/KnowledgeQaView.vue`（新增）：页面组件。
- `hragent-frontend/src/utils/qa.js`（新增）：拒答/低置信度判定与置信度格式化纯逻辑。
- `hragent-frontend/src/router/index.js`（修改）：注册 `knowledge-qa` 路由。
- `hragent-frontend/src/layouts/MainLayout.vue`（修改）：启用「知识问答」菜单项。
- `hragent-frontend/tests/qa.test.js`（新增）：前端纯逻辑单测。
- 无后端改动。
