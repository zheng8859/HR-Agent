# Spec Delta

## Purpose

定义 RBAC 授权能力：4 角色权限矩阵与 FastAPI 依赖注入（认证 → 权限 → 业务逻辑）。

## ADDED Requirements

### Requirement: 获取当前用户依赖

系统 SHALL 提供 `get_current_user` 依赖，解析 JWT、校验用户存在且启用。

#### Scenario: 有效令牌返回当前用户
- **WHEN** 以有效令牌调用受 `get_current_user` 保护的接口
- **THEN** 返回该令牌对应的启用用户

#### Scenario: 过期或缺失令牌被拒绝
- **WHEN** 以过期或缺失的令牌调用受保护接口
- **THEN** 返回未认证错误

### Requirement: 超级管理员依赖

系统 SHALL 提供 `get_current_superuser` 依赖，仅超级管理员可访问受其保护的接口。

#### Scenario: 非超管被拒绝
- **WHEN** 非超级管理员用户访问受 `get_current_superuser` 保护的接口
- **THEN** 返回无权限错误（403）

### Requirement: 角色管理员依赖

系统 SHALL 提供 `get_current_admin_by_role` 依赖，按角色判断管理员权限。

#### Scenario: 角色不满足被拒绝
- **WHEN** 角色不满足管理要求的用户访问受 `get_current_admin_by_role` 保护的接口
- **THEN** 返回无权限错误（403）

### Requirement: 4 角色权限矩阵

系统 SHALL 对 4 角色（`admin` / `hr_manager` / `hr_specialist` / `employee`）× 核心资源（招聘 / 知识 / Agent / 系统管理）× 操作做完整授权断言。

#### Scenario: 全组合授权断言成立
- **WHEN** 遍历 4 角色对核心资源的操作组合
- **THEN** 授权结果与权限矩阵完全一致（超管全权限、HR 负责人只读、HR 专员限招聘、普通员工限知识问答）
