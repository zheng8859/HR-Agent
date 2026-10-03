# recruitment Specification

## Purpose
定义招聘四环节（JD / 评分标准 / 简历评估 / 面试方案）的本地持久化能力与四实体外键闭环。

## Requirements

### Requirement: JD 状态枚举

岗位描述（JobDescription）SHALL 具备状态字段，取值为 `draft` / `published` / `archived`。

#### Scenario: 新建 JD 默认草稿
- **WHEN** 创建 JD 且未指定状态
- **THEN** 状态默认为 `draft`

### Requirement: 评分标准绑定 JD

评分标准（ScoringCriteria）SHALL 通过 `job_description_id` 外键绑定一条 JD。

#### Scenario: 评分标准引用 JD
- **WHEN** 创建评分标准并指定其 `job_description_id`
- **THEN** 评分标准与 JD 建立外键关联

### Requirement: 评分标准总分默认 100

评分标准 SHALL 具备 `total_score` 字段，未指定时默认 100。

#### Scenario: 未指定总分使用默认值
- **WHEN** 创建评分标准且不传 `total_score`
- **THEN** 总分默认为 100

### Requirement: 简历评估引用 JD 与评分标准

简历评估（ResumeEvaluation）SHALL 通过 `job_description_id` 与 `scoring_criteria_id` 两个外键分别引用本地 JD 与评分标准。

#### Scenario: 简历评估同时绑定 JD 与评分标准
- **WHEN** 创建简历评估并指定 `job_description_id` 与 `scoring_criteria_id`
- **THEN** 简历评估与两者建立外键关联

### Requirement: 简历评估状态流转

简历评估 SHALL 具备状态字段，取值为 `pending` / `rejected` / `interview`。

#### Scenario: 新建简历评估默认待处理
- **WHEN** 创建简历评估且未指定状态
- **THEN** 状态默认为 `pending`

### Requirement: 面试方案绑定已完成评估

面试方案（InterviewPlan）SHALL 通过 `resume_evaluation_id` 外键绑定一条简历评估，防止在无评估结果时生成面试方案（防空转）。

#### Scenario: 面试方案必须引用简历评估
- **WHEN** 创建面试方案并指定其 `resume_evaluation_id`
- **THEN** 面试方案与简历评估建立外键关联，且关联的评估记录必须存在
