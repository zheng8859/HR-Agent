# agent Specification

## Purpose
定义 Agent 编排层能力：意图快慢双通道、受控决策动作空间、工具注册表边界、缺口分类、高风险锁定、会话记忆与指代解析、SSE 流式协议、产物构建、审计留痕。

## Requirements

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
Agent SHALL 只能调用工具注册表内声明的工具，且注册表内 6 个招聘工具（`jd`/`jd_edit`/`criteria_edit`/`resume_screening`/`interview_plan`/`resource_delete`）SHALL 挂接真实业务服务执行（不再返回占位产物）；清单外意图明确「办不了」。

#### Scenario: 注册表内工具真实执行
- **WHEN** 用户输入「生成前端工程师 JD」且岗位名称齐备
- **THEN** 调 `job_description_service.generate_jd` 产出 `jd_confirm` 产物，而非占位产物

#### Scenario: 清单外意图
- **WHEN** 用户请求「帮我查这个候选人的社保记录」
- **THEN** 识别为 `intent=chat`（明确办不了），不触发任何工具

### Requirement: 高风险动作锁定
删除类动作 SHALL 要求确认（`requires_confirmation=True`）；未确认不执行。分两步：首轮只返回删除候选（`delete_resource_candidates`）+ `requires_confirmation=True`，不触碰数据；第二轮明确「确认删除」后才真实执行删除。

#### Scenario: 删除需确认
- **WHEN** 用户输入「删除这份 JD」
- **THEN** 返回 `intent=resource_delete`、`requires_confirmation=True`，不直接执行删除

#### Scenario: 首轮仅出候选
- **WHEN** 用户输入「删除这份 JD」
- **THEN** 返回 `intent=resource_delete`、`requires_confirmation=True`、`artifacts` 含 `delete_resource_candidates`，不执行删除

#### Scenario: 确认后执行
- **WHEN** 用户回复「确认删除这份 JD」
- **THEN** 真实调用对应删除服务，产出 `delete_resource_result`，审计记录高风险操作

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
对话流 SHALL 产出 `thinking → plan → delta → final` 事件序列；任务型流产出 `progress → delta → artifact → final`，其中每条产物（artifacts）逐条以 `artifact` 帧推送。

#### Scenario: 对话流事件顺序
- **WHEN** 发起对话请求
- **THEN** SSE 事件按 thinking、plan、delta、final 顺序推送，以 final 收尾

#### Scenario: 任务流产物帧
- **WHEN** 任务型工具产出多条 artifacts
- **THEN** 每条 artifact 依次以 `artifact` 事件推送，最后 `final` 收尾

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

### Requirement: 工具执行契约
每个工具 handler SHALL 为异步函数，返回 `ToolOutcome`（`artifacts` / `message` / `missing_fields` / `requires_confirmation` / `suggestions` / `steps`），把工具专属前置校验下沉到 handler 内，编排层仅做意图/角色/合并。

#### Scenario: 工具返回多产物与缺口
- **WHEN** 简历筛选缺附件
- **THEN** handler 返回 `missing_fields` + `resume_upload_request` 产物，编排层据此走 `ask_user`

### Requirement: 面试方案候选人四态
`interview_plan` SHALL 用 `resolve_candidate` 将候选人口语化指代解析为 `matched`/`no_match`/`ambiguous`/`no_specific` 四态，仅 `matched` 才生成方案。

#### Scenario: 候选人歧义
- **WHEN** 候选人指代命中多条
- **THEN** 返回 `interview_plan_request` 并携带候选列表，要求用户具体化，不直接生成

#### Scenario: 无匹配
- **WHEN** 候选人未找到
- **THEN** 返回 `interview_plan_request`，提示先去简历筛选

### Requirement: 简历筛选附件引导
`resume_screening` 在对话入口无附件时 SHALL 返回 `resume_upload_request` 引导（格式提示 + 选 JD + 跳转简历筛选页），不越界处理文件内容。

#### Scenario: 缺附件引导上传
- **WHEN** 用户输入「筛选这份简历」但未附带附件
- **THEN** 返回 `resume_upload_request` 产物与上传引导话术

### Requirement: 删除候选列表与确认执行
`resource_delete` SHALL 解析删除目标；多匹配返回候选列表（`delete_resource_candidates`）；确认执行时从候选/记忆定位对象，真实删除并产出 `delete_resource_result`；目标存在关联依赖时拒绝删除并说明（不级联）。

#### Scenario: 多匹配出候选
- **WHEN** 删除目标命中多条资源
- **THEN** 返回 `delete_resource_candidates` 候选列表，要求用户具体化

#### Scenario: 有依赖拒绝删除
- **WHEN** 确认删除的 JD 被评分标准/简历评估引用
- **THEN** 拒绝删除并说明关联依赖，不级联、不崩溃
