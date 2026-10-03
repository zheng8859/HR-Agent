# Design

## 目标

在现有后端新增面试方案服务，对接 `InterviewPlan` 本地表（doc 35）与 `ResumeEvaluation` 记录，实现「绑定已评估候选人 → Dify type=4 生成 → 落库 → 状态联动 → 导出」闭环。

## 端点

| 动作 | 端点 | 权限 |
|------|------|------|
| 生成 | `POST /interview-plans/generate`（`resume_evaluation_id`）→ 201 | 写（`get_current_admin_by_role`） |
| 重新生成 | `POST /interview-plans/{id}/regenerate` | 写 |
| 列表 | `GET /interview-plans` | 读（`get_current_user`，按 `user_id` 过滤） |
| 详情 | `GET /interview-plans/{id}` | 读（所有权） |
| 编辑保存 | `PUT /interview-plans/{id}`（`content`/`candidate_name`） | 写 |
| 导出 | `GET /interview-plans/{id}/export?format=md\|txt` → 文件响应 | 读（所有权） |

## 关键决策

1. **数据依赖守卫**：`generate_plan` 先 `db.get(ResumeEvaluation, resume_evaluation_id)`；不存在或非本人 → 404；`total_score is None` → 422「该简历尚未完成评估」。防空转。
2. **方案七要素落库**：`InterviewPlan.content`（Text）存 markdown，`format_plan(output)` 把 Dify 输出的七要素渲染为 `## 面试目标` 等分区。模型不加 JSONB 结构列，保持 doc 35 表结构不变。
3. **候选人解析四态**：纯函数 `resolve_candidate(query, candidates)` 返回 `CandidateResolution(state, matches, message)`；`query` 为空 → `no_specific`，`query in candidate_name` 命中 0/1/N 条 → `no_match`/`matched`/`ambiguous`。供 Agent 流程复用，本阶段以单测覆盖。
4. **状态联动幂等**：生成/重新生成后一律把关联评估 `status = interview`，重复生成不产生异常状态。
5. **导出 UTF-8 + BOM**：端点返回 `Response(content="﻿" + 正文, media_type=...)`，`Content-Disposition: attachment; filename=面试方案-{姓名}.md|txt`，Windows 记事本打开不乱码（doc 38 A4 Windows 注意）。
6. **所有权**：面试方案按 `user_id` 过滤（与简历评估一致，敏感信息不越权）。

## 测试策略

TDD：先写 `tests/test_interview_plan_service.py`（守卫/四态/七要素/状态联动/导出/重新生成/所有权）与 `tests/test_interview_plans_endpoints.py`（RBAC/守卫/导出编码），全红后实现，迭代至全绿。
