# agent-ui Specification

## Purpose
HR Agent 对话页（`HRAgentView.vue`）：SSE 流式渲染、内嵌工具面板按产物类型切换、进度折叠、建议按钮、角色快捷芯片。

## Requirements

### Requirement: 对话流式渲染
对话页 SHALL 通过 POST + `text/event-stream` 消费对话流（`thinking → plan → delta → final`），增量渲染 AI 消息文本，最终以 `final` 的完整响应收尾。

#### Scenario: 流式增量渲染
- **WHEN** 用户发送「生成 JD」
- **THEN** 前端逐 `delta` 帧增量渲染文本，`final` 帧后显示完整消息与产物

### Requirement: 内嵌工具面板
对话页 SHALL 按 `artifacts[].type` 切换内嵌面板：`jd_confirm`（JD 确认表单）、`resume_upload_request`（简历上传引导）、`interview_plan_execute`（面试方案）、`delete_resource_candidates`（删除候选确认）。

#### Scenario: 面板按产物切换
- **WHEN** 响应 artifacts 含 `jd_confirm`
- **THEN** 在对应消息下渲染 JD 确认表单面板（岗位名称/地点/薪资/经验/学历）

### Requirement: 进度折叠
对话页 SHALL 按 `steps[].status`（completed/running/pending/failed）渲染执行步骤时间轴，折叠展示。

#### Scenario: 步骤状态渲染
- **WHEN** 响应含多步 `steps`
- **THEN** 各步骤按状态着色（完成/进行中/待执行/失败）折叠展示

### Requirement: 建议按钮
对话页 SHALL 将 `suggestions` 渲染为可点击建议按钮，部分映射跳转路由，其余仅回填输入。

#### Scenario: 建议跳转
- **WHEN** 响应的 `suggestions` 含「保存并发布 JD」
- **THEN** 渲染建议按钮，点击跳转 JD 生成页或回填输入

### Requirement: 角色快捷芯片
对话页 SHALL 按角色显隐快捷芯片：HR 角色（admin/hr_manager/hr_specialist）展示招聘类芯片，employee 仅展示通用对话。

#### Scenario: 员工隐藏招聘芯片
- **WHEN** 当前用户为 employee
- **THEN** 不展示「帮我写 JD」「筛选简历」等招聘芯片
