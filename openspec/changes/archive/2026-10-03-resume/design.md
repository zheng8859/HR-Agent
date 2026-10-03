# Design

## Context

doc 35 已建好 `ResumeEvaluation` 本地表（含 `original_filename`/`file_type`/`resume_content`/`candidate_*` 字段、`total_score`、`evaluation_metrics` JSONB、状态枚举、`job_description_id`/`scoring_criteria_id`/`user_id` 外键）与 JWT/RBAC 依赖注入。doc 36 已交付 `DifyClient`（type=1/2，mock 降级）与 `JobDescription`/`ScoringCriteria` 生成能力。本变更补齐「简历评估」这一环的服务与端点。当前 Dify 未配置（无 `.env` 密钥），按 doc 37 约定测试走 mock。

## Goals / Non-Goals

**Goals:**
- 文件上传与校验（PDF/DOC/DOCX，默认 10MB，服务端强制）+ 文本提取（pdfplumber / python-docx）。
- Dify type=3 五维度评分（学历匹配度 20 / 工作经验 25 / 技能匹配度 25 / 项目经验匹配度 20 / 综合素质 10），每维度 `score/max/reason`，总分 = 维度分之和。
- 解析失败不硬评分（提取为空/失败 → 明确报错，不落库假评分）。
- 数据依赖（必须绑定存在的 JD；评分标准可选）+ 状态流转（pending → rejected/interview，HR 更新）+ 导出 + 自动匹配 JD。
- 后端权限真门 + 数据所有权（读操作按 `user_id` 过滤，简历属敏感信息）。

**Non-Goals:**
- 不做面试方案（doc 38）。
- 不做前端简历筛选页（Phase B）。
- 不接真实 Dify（未配置密钥；`run_resume_workflow` 支持 mock，配置后即可切真）。

## Decisions

1. **Dify type=3 双模式**：`DifyClient.run_resume_workflow` 复用既有 `mock_mode`（`settings.dify_configured` 为假时返回确定性 mock 评分），真实模式走 `dify_resume_workflow_id`。备选：服务层硬编码 mock——放弃，切真时改点多。

2. **上传与评估分两步**：`POST /resume-evaluation/upload`（multipart）做校验 + 提取 + 返回文本；`POST /resume-evaluation/evaluate` 接收（`resume_content` + `job_description_id` + 可选 `scoring_criteria_id`）跑评分并落库。分两步便于前端先预览文本再评分、解析失败可重传。备选：一步到位——放弃，与 doc 13「上传→选 JD→评估」交互顺序一致。

3. **解析失败不硬评分**：提取文本为空或异常时，`upload` 返回 422「无法提取文本，请上传可复制文本的简历」，绝不进入评分、不落库 0 分假结果（doc 15「宁可报错不编造」）。

4. **总分以维度之和为准**：AI 返回的维度分求和即总分，若与 AI 声称的总分不一致，以维度分之和为准（doc 37 A4「以维度分之和为准并记录告警，不虚构总分」）。

5. **状态由 HR 更新**：创建默认 `pending`，仅通过 `PATCH /{id}/status` 流转到 `interview`/`rejected`；AI 评分只产出分数与理由，不改状态（「AI 不替人做决定」）。

6. **数据所有权按 `user_id` 过滤**：列表与详情按当前登录用户 `user_id` 过滤，非本人记录 404；写操作走 `get_current_admin_by_role`。备选：全局可见——放弃，简历属个人敏感信息（doc 37 A5）。

7. **自动评估 `evaluate_resume_auto`**：不指定 JD 时由 LLM 从可用 JD 里匹配最合适的一条再评分。mock 模式下取「标题与简历岗位最接近」的启发式匹配，保证测试可跑。

## Risks / Trade-offs

- [Dify 未配置] → mock 评分与真实工作流结构可能不一致。缓解：定义清晰输出契约（五维度 + 理由），切真时仅替换实现。
- [扫描件/乱码] → 文本提取为空。缓解：明确报错引导重新上传，不编造评分。
- [旧 DOC 格式] → `python-docx` 仅支持 docx。缓解：校验阶段接受 `.doc` 但提取失败时明确提示转 docx（mock 下不真实解析二进制）。
- [维度分不配平] → 以维度之和为准，不虚构总分。

## Migration Plan

1. 无数据迁移（复用 doc 35 表），`alembic upgrade head` 无需新迁移。
2. 复用 doc 35 已声明的 `pdfplumber` / `python-docx` 依赖，无新增依赖。
3. 回滚：删除本变更新增服务/端点即可，无数据影响。

## Open Questions

（无——上传限制/维度权重/状态口径按 doc 37 + doc 15 §2.3 已明确，Dify 未配置已按 mock 决策。）
