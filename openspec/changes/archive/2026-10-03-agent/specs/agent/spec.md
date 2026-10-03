# agent Specification

## Purpose
定义 Agent 编排层能力：意图快慢双通道、受控决策动作空间、工具注册表边界、缺口分类、高风险锁定、会话记忆与指代解析、SSE 流式协议、产物构建、审计留痕。

## ADDED Requirements

### Requirement: 意图快慢双通道
Agent SHALL 先走快通道（关键词 + 附件启发式）识别意图；快通道未命中时走慢通道（受控 ReAct），慢通道失败回退快通道规则并标记 `source=fallback`。

#### Scenario: 快通道命中
- **WHEN** 用户输入「帮我生成一份前端开发工程师的 JD」
- **THEN** 返回 `intent=jd`、`route=recruitment.jd`、`source=fast`，不走慢通道

#### Scenario: 慢通道失败回退
- **WHEN** 快通道未命中且慢通道（LLM）调用失败或未配置
- **THEN** 返回快通道规则结果并标记 `source=fallback`

### Requirement: 受控决策动作空间
Agent 的决策动作 SHALL 限制为 `chat`（普通回复）、`use_tool`（调用工具）、`ask_user`（追问用户）三种。

#### Scenario: 缺信息追问
- **WHEN** 用户请求生成 JD 但未提供岗位名称
- **THEN** 动作为 `ask_user`，`missing_fields` 含 `job_title`

### Requirement: 工具注册表边界
Agent SHALL 只能调用工具注册表内声明的工具；清单外意图明确「办不了」。

#### Scenario: 清单外意图
- **WHEN** 用户请求「帮我查这个候选人的社保记录」
- **THEN** 识别为 `intent=chat`（明确办不了），不触发任何工具

### Requirement: 高风险动作锁定
删除类动作 SHALL 要求确认（`requires_confirmation=True`）；未确认不执行。

#### Scenario: 删除需确认
- **WHEN** 用户输入「删除这份 JD」
- **THEN** 返回 `intent=resource_delete`、`requires_confirmation=True`，不直接执行删除

### Requirement: 角色工具权限
员工角色（employee）SHALL 不能触发招聘工具，仅普通对话与知识问答。

#### Scenario: 员工触发招聘工具被降级
- **WHEN** employee 角色请求「生成一份 JD」
- **THEN** 降级为 `chat`，提示无权限

### Requirement: 会话记忆与指代解析
Agent SHALL 按会话读最近 12 条消息、上限 6000 字符，用于指代解析。

#### Scenario: 指代解析最近产物
- **WHEN** 用户说「帮我改一下刚才那份 JD」
- **THEN** 能从历史 assistant 消息的 artifacts 中找到最近生成的 JD

### Requirement: SSE 流式协议
对话流 SHALL 产出 `thinking → plan → delta → final` 事件序列；任务型流产出 `progress → delta → artifact → final`。

#### Scenario: 对话流事件顺序
- **WHEN** 发起对话请求
- **THEN** SSE 事件按 thinking、plan、delta、final 顺序推送，以 final 收尾

### Requirement: 返回结构契约
Agent 响应 SHALL 包含 `message / intent / route / steps / artifacts / suggestions / requires_confirmation / missing_fields` 字段。

#### Scenario: 契约字段齐全
- **WHEN** 生成 AgentChatResponse
- **THEN** 八个契约字段全部存在

### Requirement: 审计留痕
工具调用与高风险操作 SHALL 留痕（结构化日志 + Message.context）。

#### Scenario: 工具调用留痕
- **WHEN** 触发任一工具
- **THEN** 审计日志记录工具调用（用户、意图、工具、结果）
