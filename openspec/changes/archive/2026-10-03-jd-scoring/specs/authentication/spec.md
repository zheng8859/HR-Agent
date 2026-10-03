# Spec Delta

## Purpose

补齐认证链末端：密码登录签发 JWT 与当前用户查询。

## ADDED Requirements

### Requirement: 密码登录签发 JWT

系统 SHALL 提供 `/auth/login`，校验用户名密码后签发 JWT。

#### Scenario: 凭证正确
- **WHEN** 以正确用户名密码登录
- **THEN** 返回 access token

#### Scenario: 凭证错误
- **WHEN** 密码错误或用户不存在
- **THEN** 返回 401

### Requirement: 当前用户查询

系统 SHALL 提供 `/auth/me`，返回当前登录用户。

#### Scenario: 有效令牌
- **WHEN** 携带有效令牌访问 /auth/me
- **THEN** 返回当前用户信息
