# Design

## 1. 页面结构

单页聊天式布局，复用 Element Plus 既有风格（与 `KnowledgeManagementView` 一致）：

- 页头：标题「知识问答」+ 副标题 + 知识库域下拉（`全部知识库` 表示不过滤）。
- 消息流：`el-card` 内滚动列表，用户消息右对齐、助手消息左对齐。
- 空态：无消息时展示示例问题引导卡（`SUGGESTED_QUESTIONS`）。
- 底部输入区：textarea + 发送按钮 + 重新生成 / 清空对话。

## 2. 接口对接

后端 `POST /knowledge-assistant/ask` 为**非流式**接口，一次返回完整 `KnowledgeAskResponse`。前端用普通 axios POST + 按钮 loading 表达加载态，不做 SSE 流式解析（当前后端未提供流式端点）。

## 3. 三态展示

依据响应字段切换：

| 状态 | 判定 | 展示 |
|------|------|------|
| 有依据 | `answered === true` 且 `confidence >= 0.5` | 回答 + 置信度标签 + 来源片段 |
| 低置信度 | `answered === true` 且 `confidence < 0.5` | 回答 + 警示提示「置信度较低，请核对原文」 |
| 资料不足 | `answered === false` | 信息卡展示拒答文案，不渲染确定性结论 |

## 4. 来源片段

`document_chunks` 用 `el-collapse` 折叠展示：标题 = 文档名 + 相似度百分比，内容 = 片段文本。相似度用 `confidencePercent` 格式化（0.96 → 96%）。

## 5. 重新生成与清空

- 重新生成：记录最后一条用户提问，重发同一问题。
- 清空对话：重置 `messages`，回到空态。

## 6. 纯逻辑抽离

`utils/qa.js` 承载可测纯逻辑：`SUGGESTED_QUESTIONS`、`isRefusal`（`answered === false`）、`isLowConfidence`（`answered === true && confidence < 0.5`）、`confidencePercent`（置信度 → 百分比字符串）。用 `node:test` 覆盖。
