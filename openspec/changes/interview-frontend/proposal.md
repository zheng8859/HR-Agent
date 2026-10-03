# Proposal

## Why

面试方案后端能力（`interview-plan`）已落地：绑定已完成简历评估、Dify type=4 生成七要素方案、状态联动、编辑保存、导出、重新生成均已可用。但前端缺少智能面试页，HR 无法选择已评估候选人、生成并查看专属方案、编辑保存、导出与重新生成。补齐该页面即打通「JD → 评分标准 → 简历评估 → 面试方案」四环节闭环的最后一环。

## What Changes

- 新增智能面试前端页面 `SmartInterviewView`（Vue 3 + Element Plus），参考原型 `frontend/pages/smart-interview.html` 还原设计。
- 候选人选择器：仅列出「已完成简历评估」（`total_score` 非空）的候选人。
- 方案生成：选中候选人触发生成，展示 AI 生成进度态与重复提交防护。
- 方案分区展示：按面试目标/面试流程/核心问题/追问建议/考察维度/评分建议/候选人风险点七要素分区展示。
- 编辑保存、导出（TXT / Markdown）、重新生成（生成成功后候选人状态自动置为 interview）。
- 空态：无已完成评估候选人时给出「先完成简历评估」引导，并跳转简历筛选页。

## Capabilities

### New Capabilities

- `interview-ui`: 智能面试页的前端交互能力（候选人选择过滤、方案生成与七要素分区展示、编辑保存、导出、重新生成、空态）。

### Modified Capabilities

<!-- 无：后端 interview-plan 能力无 spec 级变化 -->

## Impact

- `hragent-frontend/src/api/interviewPlan.js`（新增）：对接 `/interview-plans` 端点。
- `hragent-frontend/src/views/SmartInterviewView.vue`（新增）：页面组件。
- `hragent-frontend/src/utils/interview.js`（新增）：方案 markdown 分区解析纯逻辑。
- `hragent-frontend/src/router/index.js`（修改）：注册 `interview` 路由。
- `hragent-frontend/src/layouts/MainLayout.vue`（修改）：启用「智能面试」菜单项。
- `hragent-frontend/tests/interview.test.js`（新增）：前端纯逻辑单测。
- 无后端改动。
