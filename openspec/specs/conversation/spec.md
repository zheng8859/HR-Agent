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
