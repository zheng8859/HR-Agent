# Spec Delta

## Purpose

定义简历评估能力：文件上传与校验、文本提取、AI 五维度评分（含理由）、数据依赖与状态流转、导出、自动匹配 JD。

## ADDED Requirements

### Requirement: 简历文件上传与校验

系统 SHALL 支持 PDF / DOC / DOCX 简历上传，服务端强制执行格式与大小校验（默认上限 10MB），非法输入返回明确错误。

#### Scenario: 非法格式被拒绝
- **WHEN** 上传非 PDF/DOC/DOCX 文件
- **THEN** 返回 422 并说明支持的格式

#### Scenario: 超限文件被拒绝
- **WHEN** 上传超过 10MB 的文件
- **THEN** 返回 422 并说明大小上限

### Requirement: 简历文本提取

系统 SHALL 从上传的简历提取文本：PDF 用 pdfplumber，DOCX 用 python-docx。

#### Scenario: 正常提取
- **WHEN** 上传含文本层的 PDF 或 DOCX
- **THEN** 返回提取的简历纯文本

### Requirement: 解析失败不硬评分

系统 SHALL 在简历文本提取为空或失败时返回明确错误，绝不产生 0 分假评分结果。

#### Scenario: 提取为空报错
- **WHEN** 简历无法提取出文本（扫描件/乱码）
- **THEN** 返回明确错误提示，不落库评分

### Requirement: AI 评分维度结构与理由

系统 SHALL 调用 Dify type=3 生成五维度评分，每维度携带 `score` / `max` / `reason`，总分 = 各维度得分之和。默认维度：学历匹配度 20 / 工作经验 25 / 技能匹配度 25 / 项目经验匹配度 20 / 综合素质 10。

#### Scenario: 维度完整且带理由
- **WHEN** 评分成功
- **THEN** 返回五个维度，每个维度含得分、满分与评分理由

#### Scenario: 总分以维度之和为准
- **WHEN** AI 返回的维度分之和与声称总分不一致
- **THEN** 以维度分之和作为总分，不虚构总分

### Requirement: 数据依赖校验

系统 SHALL 要求简历评估绑定存在的 `job_description_id`；`scoring_criteria_id` 可选，若提供须指向存在的评分标准。

#### Scenario: 缺失 JD 被拒绝
- **WHEN** 创建评估时未提供 JD 或 JD 不存在
- **THEN** 返回 404 或 422

#### Scenario: 评分标准可选
- **WHEN** 提供不存在的 `scoring_criteria_id`
- **THEN** 返回 404

### Requirement: 候选人状态流转

系统 SHALL 支持候选人状态 `pending` / `rejected` / `interview`，默认 `pending`，由 HR 通过状态接口更新（AI 不替人做决定）。

#### Scenario: 状态由 HR 更新
- **WHEN** HR 更新评估状态为 `interview` 或 `rejected`
- **THEN** 状态更新生效

#### Scenario: 非法状态被拒绝
- **WHEN** 更新状态为非法值
- **THEN** 返回 422

### Requirement: 评估结果导出

系统 SHALL 支持导出评估结果，包含总分、各维度得分与理由。

#### Scenario: 导出完整
- **WHEN** 调用导出接口
- **THEN** 返回总分、维度分与理由的完整结果

### Requirement: 自动评估匹配 JD

系统 SHALL 支持 `evaluate_resume_auto`：不指定 JD 时由 LLM 匹配最合适的 JD 后评估。

#### Scenario: 不指定 JD 自动匹配
- **WHEN** 调用自动评估且未指定 JD
- **THEN** 由 LLM 匹配最合适 JD 后完成评分

### Requirement: 评估记录数据所有权

系统 SHALL 保证用户只能访问自己的简历评估记录（按 `user_id` 过滤），简历属敏感个人信息。

#### Scenario: 列表按用户隔离
- **WHEN** 用户查询评估列表
- **THEN** 仅返回该用户创建的评估记录
