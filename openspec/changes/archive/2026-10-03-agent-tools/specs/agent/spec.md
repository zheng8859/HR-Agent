# agent Specification (delta)

## Purpose
把文档 43 的 stub 工具 handler 升级为真实业务执行：工具执行契约、6 工具真实 handler、删除两步确认、面试四态、简历附件引导。

## MODIFIED Requirements

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

### Requirement: SSE 流式协议
对话流 SHALL 产出 `thinking → plan → delta → final`；任务型流产出 `progress → delta → artifact → final`，其中每条产物（artifacts）逐条以 `artifact` 帧推送。

#### Scenario: 对话流事件顺序
- **WHEN** 发起对话请求
- **THEN** SSE 事件按 thinking、plan、delta、final 顺序推送，以 final 收尾

#### Scenario: 任务流产物帧
- **WHEN** 任务型工具产出多条 artifacts
- **THEN** 每条 artifact 依次以 `artifact` 事件推送，最后 `final` 收尾

## ADDED Requirements

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
`resource_delete` SHALL 解析删除目标；多匹配返回候选列表（`delete_resource_candidates`）；确认执行时从候选/记忆定位对象，真实删除并产出 `delete_resource_result`。

#### Scenario: 多匹配出候选
- **WHEN** 删除目标命中多条资源
- **THEN** 返回 `delete_resource_candidates` 候选列表，要求用户具体化
