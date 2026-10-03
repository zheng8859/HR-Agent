# scoring-criteria Specification

## Purpose
定义评分标准生成能力：维度结构、总分默认 100、权重人工确认、绑定 JD。

## Requirements

### Requirement: 评分维度结构

系统 SHALL 生成结构化评分维度，每项含 `name` / `weight` / `max_score` / `description`。

#### Scenario: 维度结构完整
- **WHEN** 生成评分标准
- **THEN** 返回维度数组，每项含 name/weight/max_score/description

### Requirement: 总分默认 100

系统 SHALL 使评分标准总分默认 100。

#### Scenario: 未指定总分
- **WHEN** 创建评分标准不传 total_score
- **THEN** 总分默认 100

### Requirement: 权重不配平人工确认

系统 SHALL 校验维度分值之和是否等于总分；不配平时返回不配平标志与差值，**不自动修正**，由人工确认后生效。

#### Scenario: 分值配平
- **WHEN** 维度 max_score 之和等于总分
- **THEN** 返回配平标志为真

#### Scenario: 分值不配平提示但不修正
- **WHEN** 维度 max_score 之和 ≠ 总分
- **THEN** 返回不配平标志与差值，保留原始维度分值，不自动改写

### Requirement: 评分标准绑定 JD

系统 SHALL 允许评分标准通过 `job_description_id` 绑定一条存在的 JD。

#### Scenario: 绑定存在 JD
- **WHEN** 创建评分标准并指定存在的 job_description_id
- **THEN** 建立关联

#### Scenario: 绑定不存在的 JD 被拒绝
- **WHEN** 指定不存在的 job_description_id
- **THEN** 返回 404

### Requirement: 评分标准 CRUD 与状态机

系统 SHALL 支持评分标准列表/详情/创建/更新/删除，状态取 `draft` / `active` / `archived`，默认 `draft`。

#### Scenario: 状态默认草稿
- **WHEN** 创建评分标准且未指定状态
- **THEN** 状态默认为 `draft`
