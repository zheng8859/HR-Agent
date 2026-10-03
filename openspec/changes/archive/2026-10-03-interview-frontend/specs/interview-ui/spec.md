# interview-ui Specification

## Purpose
定义智能面试页的前端交互能力：候选人选择与已完成评估过滤、方案生成进度态与重复提交防护、七要素分区展示、编辑保存、导出 TXT/Markdown、重新生成、空态引导。

## ADDED Requirements

### Requirement: 候选人选择与已完成评估过滤

页面 SHALL 仅列出「已完成简历评估」（`total_score` 非空）的候选人作为面试方案生成对象。

#### Scenario: 仅列已完成评估
- **WHEN** 页面加载候选人列表
- **THEN** 仅展示 `total_score` 非空的评估记录，未评分记录不进入候选列表

#### Scenario: 无候选时空态
- **WHEN** 当前无已完成评估的候选人
- **THEN** 候选人选择框禁用并展示「先完成简历评估」引导

### Requirement: 方案生成

页面 SHALL 支持选中候选人后生成面试方案，生成中展示进度态并禁止重复提交；生成成功后关联候选人状态自动置为 interview。

#### Scenario: 生成方案
- **WHEN** 选中已完成评估的候选人并触发生成
- **THEN** 调用后端生成接口，成功后展示方案内容

#### Scenario: 生成中禁止重复提交
- **WHEN** 生成请求进行中
- **THEN** 生成按钮展示加载态且不可再次点击

### Requirement: 方案七要素分区展示

页面 SHALL 按「面试目标/面试流程/核心问题/追问建议/考察维度/评分建议/候选人风险点」七要素分区展示方案内容。

#### Scenario: 七要素完整展示
- **WHEN** 方案生成成功
- **THEN** 页面按七个要素分区展示方案正文

### Requirement: 可编辑与保存

页面 SHALL 支持编辑并保存方案内容。

#### Scenario: 编辑保存
- **WHEN** 用户修改方案内容并保存
- **THEN** 调用后端更新接口，保存后的内容生效

### Requirement: 导出 TXT 与 Markdown

页面 SHALL 支持将方案导出为 TXT 或 Markdown 文件。

#### Scenario: 导出 Markdown
- **WHEN** 用户以 md 格式导出
- **THEN** 触发下载 Markdown 文件

#### Scenario: 导出 TXT
- **WHEN** 用户以 txt 格式导出
- **THEN** 触发下载 TXT 文件

### Requirement: 重新生成

页面 SHALL 支持对已生成方案重新生成，并再次触发状态联动。

#### Scenario: 重新生成
- **WHEN** 用户对已有方案触发重新生成
- **THEN** 方案内容更新且候选人状态仍为 interview

### Requirement: 空态与失败态

页面 SHALL 在无方案时展示生成引导空态，生成/保存/导出失败时展示明确错误提示。

#### Scenario: 无方案空态
- **WHEN** 选中候选人但尚未生成方案
- **THEN** 展示「点击生成面试方案」引导

#### Scenario: 失败提示
- **WHEN** 生成、保存或导出失败
- **THEN** 展示后端返回的明确错误信息
