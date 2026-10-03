# interview-plan Specification

## Purpose
定义面试方案生成与管理的后端能力：绑定已完成简历评估、Dify type=4 生成专属结构化方案、候选人解析四态、状态联动 interview、编辑保存、导出 TXT/Markdown、重新生成、数据所有权。

## Requirements

### Requirement: 数据依赖守卫

系统 SHALL 要求面试方案必须关联一条已完成的简历评估记录；未关联或评估未完成时拒绝生成。

#### Scenario: 评估不存在被拒绝
- **WHEN** 生成面试方案时提供的 `resume_evaluation_id` 不存在
- **THEN** 返回 404

#### Scenario: 评估未完成被拒绝
- **WHEN** 关联的简历评估尚无评分（`total_score` 为空）
- **THEN** 返回明确错误，不生成方案

### Requirement: 候选人解析四态

系统 SHALL 支持把候选人口语化指代解析为四种状态：`matched`（唯一命中）、`no_match`（无命中）、`ambiguous`（多命中）、`no_specific`（未指明）。

#### Scenario: 未指明
- **WHEN** 候选人指代为空
- **THEN** 返回 `no_specific` 并提示指明候选人

#### Scenario: 唯一命中
- **WHEN** 候选人指代恰好命中一条记录
- **THEN** 返回 `matched` 与命中记录

#### Scenario: 多命中歧义
- **WHEN** 候选人指代命中多条记录
- **THEN** 返回 `ambiguous` 并提示说得更具体

### Requirement: 方案七要素结构

系统 SHALL 生成包含「面试目标 / 面试流程 / 核心问题 / 追问建议 / 考察维度 / 评分建议 / 候选人风险点」七要素的结构化方案，内容基于候选人个人情况。

#### Scenario: 七要素完整
- **WHEN** 生成成功
- **THEN** 方案内容包含七个要素分区

### Requirement: 状态联动为 interview

系统 SHALL 在面试方案生成成功后，将关联的简历评估状态自动置为 `interview`。

#### Scenario: 生成后置 interview
- **WHEN** 生成面试方案成功
- **THEN** 关联简历评估状态更新为 `interview`

### Requirement: 可编辑与保存

系统 SHALL 支持编辑并保存面试方案内容。

#### Scenario: 编辑保存
- **WHEN** 用户修改方案内容并保存
- **THEN** 方案内容更新生效

### Requirement: 导出 TXT 与 Markdown

系统 SHALL 支持导出面试方案为 TXT 或 Markdown，编码为 UTF-8（带 BOM），内容不截断。

#### Scenario: 导出 Markdown
- **WHEN** 以 `md` 格式导出
- **THEN** 返回完整方案内容

#### Scenario: 导出 TXT
- **WHEN** 以 `txt` 格式导出
- **THEN** 返回完整方案内容

### Requirement: 重新生成

系统 SHALL 支持对已生成方案重新生成，并再次触发状态联动。

#### Scenario: 重新生成
- **WHEN** 对已有方案触发重新生成
- **THEN** 方案内容更新且关联评估状态仍为 `interview`

### Requirement: 数据所有权

系统 SHALL 保证用户只能访问自己创建的面试方案（按 `user_id` 过滤）。

#### Scenario: 按用户隔离
- **WHEN** 用户查询面试方案列表或详情
- **THEN** 仅返回该用户创建的方案
