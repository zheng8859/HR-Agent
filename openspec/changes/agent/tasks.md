# Tasks

## 1. Schema 契约

- [ ] 1.1 `app/schemas/agent.py`：`AgentChatResponse`（8 契约字段 + conversation_id + source）、`AgentStep`、`AgentChatRequest`、`IntentClassifyRequest/Response`。
- [ ] 1.2 `app/schemas/conversation.py`：`ConversationCreate/Read/Detail`、`MessageRead`、`FeedbackCreate`。

## 2. 意图快慢双通道

- [ ] 2.1 `app/services/intent_service.py`：`INTENT_ROUTE` + `classify_intent_fast`（关键词+附件启发式，行为与 doc 42 参考规则一致）。
- [ ] 2.2 `app/services/intent_service.py`：`plan_agent_action`（受控 ReAct，动作空间 chat/use_tool/ask_user；mock 回退 `source=fallback`）。
- [ ] 2.3 `app/evaluations/agent_eval.py`：`classify_intent_fast` 改为从 `intent_service` 引用，`AgentEvaluator` 不变。

## 3. AgentServiceCore

- [ ] 3.1 `app/services/_agent_service_core.py`：`_build_tool_registry`（6 工具）+ 角色 gating。
- [ ] 3.2 `app/services/_agent_service_core.py`：`_missing_required_fields`（JD 缺岗位名称）。
- [ ] 3.3 `app/services/_agent_service_core.py`：`_parse_delete_request` + `_fallback_parse_delete_request`（删除解析 + 正则兜底）。
- [ ] 3.4 `app/services/_agent_service_core.py`：`_build_conversation_memory`（12 条 / 6000 字符）+ `_recent_generated_resources`（指代解析）。

## 4. 工具注册表 + Skill 分发

- [ ] 4.1 `app/skills/agent_skills.py`：`AgentSkillDispatcher`（intent+phase 分发，6 工具 stub，邮件留接口）。

## 5. 编排层 + 会话 + 审计

- [ ] 5.1 `app/services/agent_service.py`：编排（意图→缺口→高风险→工具→产物→记忆）+ SSE 流式。
- [ ] 5.2 `app/services/conversation_service.py`：会话/消息 CRUD + 反馈 + 记忆组装。
- [ ] 5.3 `app/core/audit.py`：`AuditLogger`（工具调用 / 高风险留痕）。

## 6. 端点 + 路由

- [ ] 6.1 `app/api/v1/endpoints/intent.py`：POST `/intent`（意图识别）。
- [ ] 6.2 `app/api/v1/endpoints/chat.py`：POST `/chat`（SSE 对话流）+ POST `/chat/feedback`。
- [ ] 6.3 `app/api/v1/endpoints/agent.py`：POST `/agent`（任务型 SSE）。
- [ ] 6.4 `app/api/v1/endpoints/conversations.py`：会话 CRUD。
- [ ] 6.5 `app/api/v1/api.py`：注册 4 个新路由。

## 7. 测试（TDD）

- [ ] 7.1 `tests/test_agent_intent.py`：快通道意图 8 类 + 缺口 + 删除锁定 + 慢通道回退。
- [ ] 7.2 `tests/test_agent_core.py`：缺口分类、删除解析、会话记忆、指代解析、角色 gating。
- [ ] 7.3 `tests/test_agent_service.py`：编排（产物结构 8 字段齐全、高风险确认、缺失字段）。
- [ ] 7.4 `tests/test_conversation_service.py`：会话/消息 CRUD + 反馈 + 所有权。
- [ ] 7.5 `tests/test_agent_endpoints.py`：intent/chat(SSE)/agent/conversations 端点 + SSE 事件序列。

## 8. 验证

- [ ] 8.1 `pytest tests/ -m "l1 or l2 or l3"` 全绿。
- [ ] 8.2 `run_evals --tier l1,l2` 通过。
- [ ] 8.3 SSE 链路 curl 验证事件流格式（thinking→plan→delta→final）。
- [ ] 8.4 审计日志记录工具调用验证。
