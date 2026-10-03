# Design: Agent 工具与对话前端

## 数据流

```
用户输入 + 附件
      │
      ▼
意图识别（快慢双通道，43 已建）── intent / action / requires_confirmation
      │
      ▼
角色 gating（employee 降级 chat，后端强制）
      │
      ▼
AgentSkillDispatcher.dispatch(intent, params, user, db, memory)   ← 异步，真实执行
      │  └─ 每个 handler：前置校验 → 业务服务/Dify → ToolOutcome
      ▼
ToolOutcome { artifacts[], message, missing_fields[], requires_confirmation, suggestions[], steps[] }
      │
      ▼
编排层合并为 AgentChatResponse（8 契约字段）→ SSE 推送
      │
      ▼
前端 HRAgentView.vue：按 artifacts[].type 切换内嵌面板 + 进度折叠 + 建议按钮
```

## 核心契约：ToolOutcome

```python
@dataclass
class ToolOutcome:
    artifacts: list[dict]                      # 产物（jd_confirm / delete_resource_candidates / ...）
    message: str | None = None                 # 覆盖编排层默认话术（None 则用 _tool_reply）
    missing_fields: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    suggestions: list[str] = field(default_factory=list)
    steps: list[AgentStep] = field(default_factory=list)
```

每个 handler 是 `async def _handle_<intent>(params, user, db, memory) -> ToolOutcome`，
把「工具专属前置校验」从编排层下沉到 handler（面试四态、简历附件、删除候选都是工具专属）。

## 各工具 handler 逻辑

### jd（生成 JD）
1. 从 message/memory 解析岗位名称（复用 `job_description_service.parse_requirement`）。
2. 缺岗位名称 → `missing_fields=["job_title"]`，`artifacts=[requirements]`。
3. 否则 `await generate_jd(...)` → `jd_confirm` 产物（含 title/location/salary_range/experience_level/education/content）。

### jd_edit / criteria_edit（编辑）
1. 从 message/memory 解析目标标题。
2. `list_jds` / `list_scoring_criteria` 模糊匹配标题。
3. 0 命中 → `jd_edit_request`（无匹配，提示无对象）；1 命中 → `jd_edit_request`（携带对象）；N 命中 → `jd_edit_candidates`（候选列表）。

### resume_screening（简历评估）
1. 无附件（`attachments` 空）→ `resume_upload_request` 引导（提示上传 PDF/DOC/DOCX + 选 JD，附 route 跳转简历筛选页）。
2. 有附件 → 实际评估在简历筛选页完成，此处返回 `resume_screening_results`（指向最近评估结果）。

### interview_plan（面试方案）
1. `list_evaluations(user)` 取已评分候选人。
2. `resolve_candidate(query, candidates)` 四态：
   - `no_specific`（未指明姓名）→ `interview_plan_request`
   - `no_match` → `interview_plan_request`（提示先去简历筛选）
   - `ambiguous` → `interview_plan_request`（候选列表，要求具体化）
   - `matched` → `await generate_plan(...)` → `interview_plan_execute`

### resource_delete（删除资源）
1. 意图层区分「请求删除」与「确认删除」（message 含「确认」）。
2. 请求删除：`_fallback_parse_delete_request` 解析目标 → 按资源类型 `list_*` 匹配 → 多匹配 `delete_resource_candidates`，均需 `requires_confirmation=True`。
3. 确认删除：按上一轮候选（memory 中的 `delete_resource_candidates`）或重新解析，真实执行对应 `delete_*`，产出 `delete_resource_result`，审计 `log_high_risk(outcome="executed")`。

## 高风险边界（铁律 #3）

- 删除「唯一真源」仍是 `TOOL_SPECS["resource_delete"]["requires_confirmation"]=True`，编排层强制派生，不信任上游。
- 真实删除仅在「确认删除」第二轮执行；第一轮只出候选 + 确认，不触碰数据。

## 前端面板映射（artifacts[].type → kind）

| artifacts.type | 面板 | 说明 |
|---|---|---|
| `jd_confirm` | JD 确认表单 | 岗位名称/地点/薪资/经验/学历，确认保存跳 JD 页 |
| `resume_upload_request` | 简历上传引导 | 格式提示 + 选 JD + 跳转简历筛选页 |
| `interview_plan_execute` | 面试方案执行 | 展示方案三要素，跳智能面试页 |
| `delete_resource_candidates` | 删除候选确认 | 候选列表 + 明确确认交互 |

SSE 对话流 `thinking → plan → delta → final`；任务流 `progress → delta → artifact → final`（artifacts 逐条 `artifact` 帧）。

## 风险点

1. **异步化回归**：`_orchestrate` 同步 → 异步，波及 `test_agent_service.py` 与两个 SSE 端点，需逐处适配并保持 8 契约字段不变。
2. **删除两步确认状态**：第二轮「确认删除」需从 memory 找回第一轮候选，否则无法定位删除对象——正则兜底 + 候选回填。
3. **面试四态边界**：`ambiguous` 需返回候选列表而非报错；`no_match` 引导先去简历筛选。
4. **简历附件语义**：对话入口 `attachments` 仅为类型提示，实际文件内容走简历筛选页，handler 只做引导不越界。
5. **前端 SSE 资源清理**：组件卸载需 AbortController 中断流，避免泄漏。
6. **产物类型一致性**：`artifacts[].type` 与前端 kind 映射必须一致（单一枚举来源，避免漂移）。
