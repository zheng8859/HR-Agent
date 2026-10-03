# conversation Specification (delta)

## Purpose
在既有「会话/消息数据模型」基础上，新增对话/消息 CRUD、反馈评分与上下文记忆组装能力。

## ADDED Requirements

### Requirement: 会话 CRUD
用户 SHALL 能创建、列出、查看、删除（软删）自己的会话；列表与详情仅返回本人数据。

#### Scenario: 会话所有权隔离
- **WHEN** 用户 A 请求列出会话
- **THEN** 仅返回 `user_id` 等于 A 的会话，不包含他人会话

### Requirement: 消息反馈评分
用户 SHALL 能对 assistant 消息提交 1~5 分反馈评分。

#### Scenario: 提交反馈
- **WHEN** 用户对某条 assistant 消息提交评分 5
- **THEN** 该消息的 `feedback_score` 更新为 5

### Requirement: 上下文记忆组装
Agent SHALL 能从会话消息中组装上下文记忆：最近 12 条、上限 6000 字符。

#### Scenario: 记忆截断
- **WHEN** 会话历史消息字符数超过 6000
- **THEN** 记忆按从新到旧累计，超限即截断，不超过 6000 字符
