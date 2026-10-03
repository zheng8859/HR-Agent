# Proposal

## Why

招聘四环节、知识助理、系统管理已各自可用，但系统缺一个「对话入口」把用户的自然语言转成受控业务动作。用户现在得自己在功能页点来点去；"帮我生成一份前端工程师的 JD"这句话没有落点。本变更落地 **Agent 编排核心架构**（文档 43）：Gateway 认证 → 意图快慢双通道 → 受控 ReAct → 工具注册表 → Skill 分发 → 缺口分类 → 高风险锁定 → SSE 流式 → 会话记忆 → 产物构建。

核心是「受控自动化」：Agent 不是无限自主的通用智能体，而是受控工具编排层——决策动作只有 `chat / use_tool / ask_user` 三种，工具只能选注册表内 6 个，删除必须确认，AI 出初稿、人定终稿。

## What Changes

- **意图双通道**（`intent_service.py`）：快通道 `classify_intent_fast`（关键词 + 附件启发式，与 doc 42 `agent_eval` 参考规则行为一致）+ 慢通道 `plan_agent_action`（受控 ReAct，动作空间 `chat/use_tool/ask_user`，LLM 失败回退 `source=fallback`）。
- **AgentServiceCore**（`_agent_service_core.py`）：工具注册表、缺口分类（缺信息/缺确认）、高风险锁定（删除）、会话记忆（12 条 / 6000 字符）、指代解析（`_recent_generated_resources`）。
- **工具注册表 + Skill 分发**（`agent_skills.py`）：6 工具 handler 均为 stub（真实实现见文档 44）；`AgentSkillDispatcher` 按 intent+phase 分发，邮件 Skill 留接口。
- **编排层**（`agent_service.py`）：Gateway 角色注入 → 意图识别 → 缺口分类 → 高风险校验 → 工具执行 → 产物构建 → 会话记忆 → SSE。
- **SSE 流式协议**：对话流 `thinking → plan → delta → final`；任务型 `progress → delta → artifact → final`（复用 doc 42 `build_sse_event`）。
- **对话/消息 CRUD**（`conversation_service.py` + `conversations.py` 端点）：会话生命周期、消息父子链、反馈评分。
- **产物构建**：18 种 artifacts + `AgentChatResponse` 组装（message/intent/route/steps/artifacts/suggestions/requires_confirmation/missing_fields）。
- **审计留痕**（`audit.py`）：工具调用与高风险操作结构化日志 + 落 Message.context。

## Capabilities

### New Capabilities

- `agent`: 意图快慢双通道、受控 ReAct、工具注册表、缺口分类、高风险锁定、会话记忆、SSE 流式协议、产物构建、审计留痕。

### Modified Capabilities

- `conversation`: 由「数据模型」扩展为「数据模型 + 对话/消息 CRUD + 反馈评分 + 上下文记忆组装」。

## Impact

- `hragent-backend/app/schemas/agent.py`（填充）：`AgentChatResponse` / `AgentStep` / 意图/请求 schema。
- `hragent-backend/app/schemas/conversation.py`（填充）：会话/消息/反馈 schema。
- `hragent-backend/app/services/_agent_service_core.py`（填充）：AgentServiceCore（注册表/缺口/高风险/记忆/指代）。
- `hragent-backend/app/services/intent_service.py`（填充）：快慢双通道（`classify_intent_fast` 为规范实现，`agent_eval` 改为引用）。
- `hragent-backend/app/services/agent_service.py`（填充）：编排层 + SSE 流式。
- `hragent-backend/app/services/conversation_service.py`（新增）：对话/消息 CRUD + 记忆组装。
- `hragent-backend/app/core/audit.py`（新增）：AuditLogger。
- `hragent-backend/app/skills/agent_skills.py`（填充）：AgentSkillDispatcher + 6 stub 工具。
- `hragent-backend/app/api/v1/endpoints/{agent,chat,intent,conversations}.py`（填充）：端点。
- `hragent-backend/app/api/v1/api.py`（修改）：注册新路由。
- `hragent-backend/app/evaluations/agent_eval.py`（修改）：`classify_intent_fast` 改为从 `intent_service` 引用（消除双实现漂移）。
- `hragent-backend/tests/test_agent_*.py`（新增）：意图/核心/编排/端点/会话测试。
- 无前端改动（对话前端属文档 44）。

## Out of Scope

- 6 个工具的真实 handler（JD/评分/简历/面试/删除/编辑）—— 文档 44 实现，本期为 stub。
- 邮件通知 / 试卷生成（`email_notification` / `exam_generate` 本期不做，仅注册表留边界）。
- 对话页前端（内嵌面板、SSE 渲染）—— 文档 44。
- 真实 LLM 慢通道接入（有 key 才走 Qwen，无 key 走 `source=fallback`）。
