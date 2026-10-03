# authentication Specification

## Purpose
定义 JWT 认证能力：OAuth2 密码流签发令牌、bcrypt 密码哈希、令牌校验/过期/篡改防护。

## Requirements

### Requirement: OAuth2 密码流签发 JWT

系统 SHALL 支持以用户名+密码（OAuth2 密码流）换取 JWT 访问令牌。

#### Scenario: 正确凭证换发令牌
- **WHEN** 以正确用户名与密码请求登录
- **THEN** 返回签发的 JWT 令牌，且令牌可被后续校验通过

### Requirement: 密码 bcrypt 哈希

系统 SHALL 使用 bcrypt 哈希存储密码，绝不存明文。

#### Scenario: 密码以哈希形式存储
- **WHEN** 创建或更新用户密码
- **THEN** 存储值为 bcrypt 哈希，且可通过哈希校验原始密码

### Requirement: JWT 编解码校验

系统 SHALL 能对签发的 JWT 正确解码并校验其签名。

#### Scenario: 有效令牌解码成功
- **WHEN** 使用系统密钥校验一个未过期、未篡改的令牌
- **THEN** 成功解出 payload 中的用户标识与过期时间

### Requirement: JWT 过期拒绝

系统 SHALL 拒绝已过期的 JWT。

#### Scenario: 过期令牌被拒绝
- **WHEN** 校验一个 `exp` 已过期的令牌
- **THEN** 校验失败并返回未认证错误

### Requirement: JWT 篡改防护

系统 SHALL 拒绝被篡改的 JWT（签名不匹配）。

#### Scenario: 篡改令牌签名校验失败
- **WHEN** 校验一个 payload 被改动但签名未重新计算的令牌
- **THEN** 签名校验失败，令牌被拒绝
