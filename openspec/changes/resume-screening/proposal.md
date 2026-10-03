# Proposal

## Why

简历评估后端能力（`resume-evaluation`）已落地：上传校验、文本提取、AI 五维度评分（含理由）、状态流转、导出均已可用。但前端缺少简历筛选页，HR 无法上传简历、触发评估、查看维度分与理由、流转候选人状态、导出报告。补齐该页面即打通「JD → 评分标准 → 简历评估」的招聘闭环。

## What Changes

- 新增简历筛选前端页面 `ResumeScreeningView`（Vue 3 + Element Plus）。
- 上传区：支持点击/拖拽上传 PDF/DOC/DOCX，格式或大小不符给出与后端一致的明确提示。
- 评估配置：选择岗位 JD（必选）与评分标准（可选），触发智能评估。
- 候选人列表：表格展示候选人/应聘岗位/工作年限/学历/毕业院校/AI 综合得分/评估状态，行点击联动评分卡。
- 评分卡：展示总分 + 各维度 `score/max/reason` 与进度条，评分结果以接口返回为准，不前端臆算。
- 状态流转：候选状态下拉（`pending`/`interview`/`rejected`）由 HR 操作，写操作走后端权限校验。
- 导出报告：将评估结果导出为可下载文本报告。
- 空态（无评估记录）与评估中进度态、重复提交防护。

## Capabilities

### New Capabilities

- `resume-screening-ui`: 简历筛选页的前端交互能力（上传校验、评估触发、评分卡展示、状态流转、导出、空态）。

### Modified Capabilities

<!-- 无：后端 resume-evaluation 能力无 spec 级变化 -->

## Impact

- `hragent-frontend/src/api/resumeEvaluation.js`（新增）：对接 `/resume-evaluation` 端点。
- `hragent-frontend/src/views/ResumeScreeningView.vue`（新增）：页面组件。
- `hragent-frontend/src/utils/resume.js`（新增）：前端文件校验与进度条百分比纯逻辑。
- `hragent-frontend/src/router/index.js`（修改）：注册 `resume-screening` 路由。
- `hragent-frontend/src/layouts/MainLayout.vue`（修改）：启用「简历筛选」菜单项。
- `hragent-frontend/tests/resume.test.js`（新增）：前端纯逻辑单测。
- 无后端改动。
