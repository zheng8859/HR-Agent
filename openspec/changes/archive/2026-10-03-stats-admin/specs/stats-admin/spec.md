# stats-admin Specification

## Purpose
定义统计看板聚合、用户管理、角色管理、超管权限隔离与内置角色保护的后端能力。

## ADDED Requirements

### Requirement: 统计看板聚合

系统 SHALL 提供概览卡、招聘统计、对话统计、近 30 天趋势与最近活动。

#### Scenario: 概览与招聘对话统计
- **WHEN** 管理员请求看板
- **THEN** 返回各域计数、环比、招聘统计与对话统计

#### Scenario: 近 30 天趋势
- **WHEN** 请求趋势数据
- **THEN** 返回近 30 天逐日计数，缺日补 0

#### Scenario: 最近活动
- **WHEN** 请求最近活动
- **THEN** 返回跨域最近记录，按时间降序

### Requirement: 统计口径可追溯

系统 SHALL 明确计数类指标的数据来源表与过滤条件，环比使用近 30 天与前一 30 天。

#### Scenario: 计数与环比
- **WHEN** 计算概览计数与环比
- **THEN** 计数来源明确，环比 = 近 30 天与前一 30 天增减

### Requirement: 用户管理

系统 SHALL 提供用户 CRUD（仅超管），字段完整，密码哈希存储且响应不回传。

#### Scenario: 创建与列表
- **WHEN** 超管创建/列出用户
- **THEN** 字段完整（用户名/邮箱/密码/姓名/手机号/部门/职位/员工编号/角色/是否启用）

#### Scenario: 密码不回传
- **WHEN** 返回用户数据
- **THEN** 响应不含密码哈希

### Requirement: 角色管理

系统 SHALL 提供角色 CRUD（仅超管），预置 4 个内置角色并标记 `is_builtin`。

#### Scenario: 内置角色预置
- **WHEN** 列出角色
- **THEN** 存在 4 个内置角色（admin/hr_manager/hr_specialist/employee），标记内置

### Requirement: 内置角色保护

系统 SHALL 禁止删除内置角色。

#### Scenario: 删除内置角色被拒
- **WHEN** 删除 `is_builtin` 角色
- **THEN** 返回 409，角色不被删除

### Requirement: 超管权限隔离

系统 SHALL 对系统管理接口强制超管校验；非超管访问返回 403。

#### Scenario: 非超管 403
- **WHEN** 非超管访问 /users 或 /roles
- **THEN** 返回 403
