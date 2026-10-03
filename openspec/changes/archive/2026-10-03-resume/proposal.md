# Proposal

## Why

招聘四环节已交付前两环（doc 36：JD 生成 + 评分标准）。`ResumeEvaluation` 表（doc 35）已具备数据结构，但简历评估这一环仍停留在「数据模型」层面：没有文件上传与文本提取、没有 Dify type=3 AI 评分、没有维度分与理由的落库、也没有对外 API 端点。本变更把第三环「简历评估」的生成能力落到后端——AI 出评分初稿、HR 定状态，可解释才可信。

## What Changes

- `app/core/config.py`：新增 `dify_resume_workflow_id`（type=3）与上传限制（默认 10MB、PDF/DOC/DOCX）。
- `app/services/dify_service.py`：`DifyClient` 新增 `run_resume_workflow`（type=3），无密钥时返回确定性 mock（五维度 + 理由）。
- `app/schemas/resume_evaluation.py`：请求/响应 Pydantic schema（维度 `name/score/max/reason`、状态 `pending/rejected/interview`、导出结构）。
- `app/services/resume_evaluation_service.py`：文件校验、文本提取（PDF→pdfplumber、DOCX→python-docx）、Dify 评分、维度/理由解析、CRUD、状态流转、导出、自动匹配 JD。
- `app/api/v1/endpoints/resume_evaluation.py`：REST 端点（上传/评估/自动评估/CRUD/状态/导出），写操作走 `get_current_admin_by_role`，读操作按 `user_id` 过滤（数据所有权）。
- 测试：文件校验、文本提取、五维度评分、解析失败不评分、状态流转、数据依赖、导出、权限与所有权。

**本期不建**：面试方案（doc 38）；前端简历筛选页（Phase B，本变更仅后端）。

## Capabilities

### New Capabilities

- `resume-evaluation`: 简历评估——文件上传与校验、文本提取、AI 五维度评分（含理由）、数据依赖与状态流转、导出、自动匹配 JD。

### Modified Capabilities

（无。`recruitment` 能力已覆盖数据模型层面的外键与状态枚举，本变更只新增行为能力，不改动其 requirement。）

## Impact

- 代码：`app/core/config.py`、`app/services/dify_service.py`、`app/services/resume_evaluation_service.py`、`app/schemas/resume_evaluation.py`、`app/api/v1/endpoints/resume_evaluation.py`、`app/api/v1/api.py`。
- 依赖：复用 doc 35 已声明的 `pdfplumber` / `python-docx` / `httpx`，无新增依赖。
- 数据库：无表结构变更（复用 doc 35 的 `resume_evaluations`）。
- 无 BREAKING 变更（全部为新增服务/端点/配置）。
