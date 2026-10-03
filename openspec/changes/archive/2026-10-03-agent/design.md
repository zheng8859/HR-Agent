# Design — Agent 编排架构

## 数据流

```
POST /chat (message, conversation_id, attachments)
  → Gateway: get_current_user（JWT + 角色注入）
  → IntentClassifier.classify()
      fast = classify_intent_fast(message, attachments)   # 关键词+附件
      if fast.intent != "chat": return fast(source="fast")
      else: return plan_agent_action(...)                  # 慢通道 / fallback
  → AgentServiceCore.handle()
      1. 角色 gating（employee 触发招聘工具 → 降级 chat）
      2. 缺口分类（jd 缺岗位名称 → ask_user + missing_fields）
      3. 高风险锁定（resource_delete → requires_confirmation=True）
      4. SkillDispatcher.dispatch(intent, phase)          # stub
      5. ArtifactBuilder.build(intent, ...)               # artifacts
      6. ContextManager 记忆写入（user/assistant 消息落库）
  → SSEStream 产出 thinking→plan→delta→final（chat）/ progress→delta→artifact→final（task）
  → AuditLogger 留痕（工具调用 + 高风险）
```

## 组件边界

| 组件 | 输入 | 输出 | 依赖 |
|------|------|------|------|
| Gateway | Authorization header | User（含 role） | deps.get_current_user |
| IntentClassifier | message + attachments + memory | intent/route/tool/requires_confirmation/missing_fields/source | eval_utils 契约常量 |
| AgentServiceCore | 分类结果 + User + messages | 决策（chat/use_tool/ask_user）+ artifacts | 工具注册表、interview_plan_service |
| SkillDispatcher | intent + phase + 参数 | stub 产物 | — |
| ConversationService | user + 会话/消息 | 持久化记录 | Conversation/Message 模型 |
| ContextManager | messages | 记忆文本（≤6000 字符）+ 最近产物 | Message.context |
| ArtifactBuilder | intent + 工具结果 | 18 种 artifact | — |
| SSEStream | 事件 dict | SSE 帧 | eval_utils.build_sse_event |
| AuditLogger | 调用上下文 | 结构化日志 + Message.context | logging |

## 架构审查要点（/plan-eng-review）

1. **意图误判兜底**：快通道兜底 `chat`；慢通道失败回退快通道规则并标 `source=fallback`。误判的最终兜底是「宁可回复闲聊，不误删数据」——删除意图必须 `requires_confirmation=True`，不确认不执行。
2. **高风险边界在后端**：`resource_delete` 的确认判定在 `classify_intent_fast`（后端规则）而非前端；前端只渲染确认表单。employee 角色无法触发招聘工具（后端角色 gating）。
3. **SSE 事件顺序**：单一生成器按 `thinking→plan→delta→final` 顺序 yield；异常统一 `error` 事件收尾，不产生半截 `final`。
4. **会话记忆预算**：按「条数（12）+ 字符（6000）」双重截断，`_build_conversation_memory` 从新到旧累计，超限即停，避免 token 失控。
5. **工具边界**：`_build_tool_registry` 只登记 6 个 intent；分发前校验 intent ∈ 注册表；`email_notification`/`exam_generate` 仅保留边界不注册 handler。
6. **耦合风险**：快通道规则与 doc 42 评测参考规则共享单一实现（`agent_eval` 改为从 `intent_service` 引用），消除「实现/评测」双写漂移。
7. **慢通道无限循环**：本期慢通道为受控单步（无 ReAct 循环），LLM 未接入时直接 `source=fallback`；未来多步时加步数上限。

## 关键决策记录

- **快通道为规范实现**：`intent_service.classify_intent_fast` 是唯一实现，`agent_eval.classify_intent_fast` 改为引用（doc 42 原为参考规则，doc 43 起收敛为同一函数）。
- **审计不走新表**：10 张本地表不含审计表；留痕用结构化日志（`hragent.audit` logger）+ Message.context JSONB（可查、可复用），符合「AI 对话记录中等敏感」分级。
- **缺口最小化**：Agent 层只追问「岗位名称」这一最小信号；地点/薪资/经验/学历由前端 JD 表单（doc 44）收集，避免对话内连环追问。
