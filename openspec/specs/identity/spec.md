# identity Specification

## Purpose
定义用户与角色的持久化能力：账号字段、4 角色代码枚举、用户-角色多对多关联，以及公共字段继承。

## Requirements

### Requirement: 公共字段继承

所有模型 SHALL 继承统一基类，自动获得 `id`(UUID)、`created_at`、`updated_at`、`is_active`、`created_by`、`updated_by` 字段。

#### Scenario: 创建实体自动填充公共字段
- **WHEN** 创建任意本地实体
- **THEN** 记录具备 UUID 主键与创建/更新时间戳，且 `is_active` 默认启用

### Requirement: 用户账号唯一性

用户表的 `username` 与 `email` SHALL 各自唯一。

#### Scenario: 用户名重复被拒绝
- **WHEN** 尝试以已存在的 `username` 创建第二个用户
- **THEN** 数据库唯一约束拒绝写入

#### Scenario: 邮箱重复被拒绝
- **WHEN** 尝试以已存在的 `email` 创建第二个用户
- **THEN** 数据库唯一约束拒绝写入

### Requirement: 角色代码枚举

用户角色 SHALL 仅为 4 种代码枚举：`admin` / `hr_manager` / `hr_specialist` / `employee`。

#### Scenario: 非法角色值被拒绝
- **WHEN** 以枚举之外的字符串作为角色写入
- **THEN** 校验拒绝该值

### Requirement: 用户-角色多对多关联

用户与角色 SHALL 通过 `user_role` 中间表多对多关联，角色具备 `name`(唯一)、`description`、`is_builtin`。

#### Scenario: 一个用户关联多个角色
- **WHEN** 通过中间表为用户分配多个角色
- **THEN** 关联关系成立且可反向查询
