# Change: 实现 Agent 招聘 6 工具与对话前端

## Why

文档 43 搭好了 Agent 编排骨架（Gateway / 意图双通道 / 工具注册表 / SSE / 会话记忆），但 6 个工具 handler 仍为 stub（`_stub_artifact` 返回占位产物），"说一句话 → 先把活办了"尚未真正跑通。本文档把 6 个工具接到真实业务服务（JD / 评分标准 / 简历评估 / 面试方案 / 删除），并完成对话前端（内嵌面板 + 流式渲染），让用户能在对话入口完成招聘四环节的关键动作，全程受控、可确认、可追溯。

## What Changes

### 后端

- **Skill 分发器异步化**：`AgentSkillDispatcher.dispatch` 由「同步返回单产物」升级为「异步返回 `ToolOutcome`（多产物 + 缺口 + 确认 + 步骤 + 建议）」，承载每个工具的**前置校验 → 执行 → 产物构建**闭环。
- **编排层异步化**：`_orchestrate` / `handle_message` / `stream_chat` / `stream_agent` 改为异步，注入 `AsyncSession`，工具执行可访问 DB 与 Dify。
- **6 个真实工具 handler**（挂到 43 的注册表 `TOOL_SPECS`）：
  - `jd`：校验岗位名称（缺则 `missing_fields`）→ 调 type=1 生成初稿 → `jd_confirm` 面板产物
  - `jd_edit`：按标题定位 JD（多匹配 → `jd_edit_candidates`；单匹配 → `jd_edit_request`）
  - `criteria_edit`：定位评分标准（多匹配 → `criteria_edit_candidates`；单匹配 → `criteria_edit_request`）
  - `resume_screening`：无附件/未选 JD → `resume_upload_request` 上传引导；已上传 → `resume_screening_results`
  - `interview_plan`：`resolve_candidate` 四态（matched/no_match/ambiguous/no_specific）→ `interview_plan_request` 或 `interview_plan_execute`
  - `resource_delete`：解析删除目标（多匹配 → `delete_resource_candidates` 候选列表）→ 明确确认后执行 → `delete_resource_result`
- **删除两步确认**：区分「首次请求（出候选 + 二次确认）」与「确认执行（真实删除 + 审计）」，后端强制、不依赖前端。

### 前端

- **`HRAgentView.vue` 对话页**：消息气泡 + 内嵌面板（按 `artifacts[].type` 切换 kind）+ 进度折叠（`steps[].status`）+ 建议按钮（`suggestions`）+ 快捷芯片（角色显隐）。
- **`api/agent.js`**：对话/任务 SSE 流式客户端 + 会话列表 + 反馈。
- 路由 `/agent` + 侧边菜单「HR Agent」入口。

## Capabilities

- `agent`（MODIFIED）：工具 handler 由 stub 升级为真实执行契约。
- `agent-ui`（ADDED）：对话前端内嵌面板 / SSE 渲染 / 角色芯片。

## Impact

- 影响 `app/skills/agent_skills.py`、`app/services/agent_service.py`、`app/services/intent_service.py`（删除确认识别）。
- 复用既有业务服务 `job_description_service` / `scoring_criteria_service` / `resume_evaluation_service` / `interview_plan_service`，不重复实现生成逻辑。
- 前端新增 `HRAgentView.vue`、`api/agent.js`，改 `router/index.js`、`MainLayout.vue`。
- 既有测试 `test_agent_service.py`（`_orchestrate` 同步调用）需随异步化调整。

## Out of Scope

- 邮件通知 / 试卷生成（注册表留 `email_notification`、`exam_generate` 位，Skill 留接口，本期不做）。
- 真实慢通道 LLM（受控 ReAct）仍为 stub，删除目标解析用正则兜底。
- 前端 `email_confirm` / `exam_document_upload` / `exam_generate` 面板本期不做。
