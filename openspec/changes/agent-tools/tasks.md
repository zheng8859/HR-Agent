# Tasks

## 1. Skill 分发器异步化

- [ ] 1.1 `app/skills/agent_skills.py`：新增 `ToolOutcome`（artifacts / message / missing_fields / requires_confirmation / suggestions / steps）。
- [ ] 1.2 `AgentSkillDispatcher.dispatch(intent, params, user, db, memory)` 改为 async，返回 `ToolOutcome`；清单外抛 ValueError。
- [ ] 1.3 删除 `_stub_artifact` / `ARTIFACT_BY_INTENT`（stub 语义），由各 handler 直接构建产物。

## 2. 6 工具真实 handler

- [ ] 2.1 `jd`：解析岗位名称 → 缺则 `missing_fields=["job_title"]` + `requirements` 产物；否则调 `job_description_service.generate_jd` → `jd_confirm` 产物。
- [ ] 2.2 `jd_edit`：按标题定位 JD（`list_jds` + 标题模糊匹配）→ 0/1/N 命中分别 `jd_edit_request`（无匹配）/ `jd_edit_request`（单）/ `jd_edit_candidates`（多）。
- [ ] 2.3 `criteria_edit`：定位评分标准 → `criteria_edit_request` / `criteria_edit_candidates`。
- [ ] 2.4 `resume_screening`：无附件 → `resume_upload_request` 引导（+ missing_fields）；已上传 → `resume_screening_results`。
- [ ] 2.5 `interview_plan`：`resolve_candidate` 四态 → `interview_plan_request`（no_match/ambiguous/no_specific）或 `interview_plan_execute`（matched 调 `generate_plan`）。
- [ ] 2.6 `resource_delete`：区分「首次请求（`delete_resource_candidates` + 二次确认）」与「确认执行（真实删除 + `delete_resource_result`）」；支持 JD/评分标准/简历/面试方案删除。

## 3. 编排层异步化

- [ ] 3.1 `app/services/agent_service.py`：`_orchestrate` 改 async，接收 `db`，工具分支改 `await skill_dispatcher.dispatch(...)`。
- [ ] 3.2 `handle_message` / `stream_chat` / `stream_agent` 传递 `db`，工具产物与缺口/确认从 `ToolOutcome` 合并。
- [ ] 3.3 `intent_service.classify_intent_fast`：删除分支区分「确认删除」（含「确认」）与「请求删除」，返回标志供 handler 判定执行/候选。

## 4. 前端 API 客户端

- [ ] 4.1 `src/api/agent.js`：`streamChat` / `streamAgent`（SSE 流，复用 `utils/sse.js`）、`listConversations`、`sendFeedback`、`intent`。
- [ ] 4.2 复用 `utils/token.js` 注入 Bearer，POST + `text/event-stream` 手动解析。

## 5. 前端对话页

- [ ] 5.1 `src/views/HRAgentView.vue`：消息气泡列表 + 输入区 + 附件入口 + 快捷芯片（HR 角色显隐）。
- [ ] 5.2 内嵌面板按 `artifacts[].type` 切换：`jd_confirm` / `resume_upload` / `interview_plan` / `delete_resource_candidates`。
- [ ] 5.3 进度折叠：`steps[].status`（completed/running/pending/failed）渲染时间轴。
- [ ] 5.4 建议按钮：`suggestions` 渲染，可映射跳转路由。
- [ ] 5.5 路由 `/agent` + `MainLayout.vue` 菜单「HR Agent」入口。

## 6. 测试（TDD）

- [ ] 6.1 `tests/test_agent_skills.py`：6 工具 handler 的前置校验 / 产物类型 / 缺口 / 删除两步确认。
- [ ] 6.2 更新 `tests/test_agent_service.py`：`_orchestrate` 异步化适配 + 工具产物合并。
- [ ] 6.3 `tests/test_agent_endpoints.py`：工具真实产物的 SSE 事件序列（artifact 帧）。
- [ ] 6.4 `tests/test_agent_intent.py`：删除「确认」识别。

## 7. 验证

- [ ] 7.1 `pytest tests/ -m "not slow"` 全绿。
- [ ] 7.2 `run_evals --tier all --compare baseline.json` L1/L2 达标。
- [ ] 7.3 前后端联调：对话「生成 JD」→ jd_confirm 面板 → 保存；「删除 XX」→ 候选确认 → 执行。
- [ ] 7.4 前端构建通过（`npm run build` 或 dev server 无报错）。
