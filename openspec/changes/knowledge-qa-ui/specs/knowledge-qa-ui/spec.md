# knowledge-qa-ui Specification

## Purpose
定义知识问答前端页面的交互能力：提问与回答展示、来源片段展开核对、低置信度/资料不足三态、空态示例问题引导、重新生成、知识库域选择。

## ADDED Requirements

### Requirement: 问答交互

系统 SHALL 允许用户输入问题并发送，展示 AI 回答与来源片段。

#### Scenario: 提问展示回答与来源
- **WHEN** 用户输入问题并发送
- **THEN** 展示回答，并附带可展开的来源片段（`document_chunks`）

### Requirement: 来源片段可展开核对

系统 SHALL 以可展开形式展示来源片段，含文档名与相似度。

#### Scenario: 来源可核对
- **WHEN** 回答附带来源片段
- **THEN** 每个片段可展开查看原文，并展示文档名与置信度百分比

### Requirement: 低置信度提示

系统 SHALL 在回答有依据但置信度偏低时给出提示。

#### Scenario: 低置信度警示
- **WHEN** 回答 `answered` 为 true 且 `confidence < 0.5`
- **THEN** 展示「置信度较低」警示，提示核对原文

### Requirement: 无依据拒答态

系统 SHALL 在无依据时展示「资料不足」，不渲染确定性结论。

#### Scenario: 资料不足展示
- **WHEN** 响应 `answered` 为 false
- **THEN** 展示资料不足提示，不显示确定性答案样式

### Requirement: 空态示例问题引导

系统 SHALL 在无对话时展示示例问题引导，点击回填输入框。

#### Scenario: 空态引导
- **WHEN** 尚未发起任何对话
- **THEN** 展示示例问题，点击可回填输入框

### Requirement: 重新生成

系统 SHALL 支持重新生成最后一条提问的回答。

#### Scenario: 重新生成
- **WHEN** 用户点击重新生成
- **THEN** 重发最后一条用户提问并更新回答
