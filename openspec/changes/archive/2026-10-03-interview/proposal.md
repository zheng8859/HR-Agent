# Proposal

## Why

简历评估（`resume-evaluation`）已产出带维度分与理由的候选人记录，但招聘闭环的最后一步「面试方案」缺失——面试官无法基于已评分候选人获得专属的结构化面试方案。补齐后即打通「JD → 评分标准 → 简历评估 → 面试方案」四环节闭环。

## What Changes

- 新增面试方案服务：读取已评分候选人与关联 JD，调用 Dify type=4 生成专属方案并落库。
- 数据依赖守卫：面试方案**必须关联一条已完成的简历评估**（防空转），未关联或未完成时明确拒绝。
- 候选人解析四态：`matched / no_match / ambiguous / no_specific`，供 Agent 解析候选人口语化指代。
- 方案七要素结构：面试目标 / 流程 / 核心问题 / 追问建议 / 考察维度 / 评分建议 / 候选人风险点，内容基于候选人个人情况而非通用模板。
- 状态联动：生成成功后，对应简历评估状态自动置为 `interview`。
- 可编辑、保存、导出（TXT / Markdown，UTF-8 + BOM）、重新生成。

## Capabilities

### New Capabilities

- `interview-plan`: 面试方案生成与管理的后端能力（数据依赖守卫、专属方案生成、状态联动、导出、重新生成、所有权）。

### Modified Capabilities

<!-- 无 -->

## Impact

- `hragent-backend/app/core/config.py`（修改）：新增 `dify_interview_workflow_id`（type=4）。
- `hragent-backend/app/services/dify_service.py`（修改）：新增 `run_interview_workflow` + `MOCK_INTERVIEW_OUTPUT`。
- `hragent-backend/app/schemas/interview_plan.py`（新增实现）。
- `hragent-backend/app/services/interview_plan_service.py`（新增实现）。
- `hragent-backend/app/api/v1/endpoints/interview_plans.py`（新增实现）。
- `hragent-backend/app/api/v1/api.py`（修改）：注册 `/interview-plans` 路由。
- `hragent-backend/tests/`（新增）：面试方案服务与端点测试。
