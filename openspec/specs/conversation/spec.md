# conversation Specification

## Purpose
定义会话与消息的持久化能力：会话生命周期状态、消息角色，以及消息父子链自引用。

## Requirements

### Requirement: 会话生命周期状态

会话 SHALL 具备状态字段，取值为 `active` / `archived` / `deleted`。

#### Scenario: 新建会话默认激活
- **WHEN** 创建一条会话且未指定状态
- **THEN** 状态默认为 `active`

### Requirement: 消息角色

消息 SHALL 记录发送方角色，取值为 `user` / `assistant` / `system`。

#### Scenario: 消息记录角色
- **WHEN** 创建一条消息并指定角色
- **THEN** 消息持久化该角色值

### Requirement: 消息父子链

消息 SHALL 支持通过 `parent_message_id` 自引用形成父子链。

#### Scenario: 回复消息引用父消息
- **WHEN** 创建一条消息并设置其 `parent_message_id` 指向同会话内另一条消息
- **THEN** 两条消息构成父子关系且可沿链追溯

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
