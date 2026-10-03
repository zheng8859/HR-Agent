# Spec Delta

## Purpose

定义 JD 生成能力：双入口（表单直生 / 一句话解析）、SSE 流式、CRUD 与状态机。

## ADDED Requirements

### Requirement: JD 双入口生成

系统 SHALL 支持两种 JD 生成入口：表单字段直接生成，与一句话描述先解析成结构化字段再生成。

#### Scenario: 表单直生
- **WHEN** 提交完整表单字段
- **THEN** 直接生成 JD 正文与结构化字段

#### Scenario: 一句话解析后生成
- **WHEN** 仅提供一句话描述
- **THEN** 先解析为结构化字段，再据此生成 JD

### Requirement: JD 必填校验

系统 SHALL 要求岗位名称或岗位需求描述至少一项；保存时标题与正文必填。

#### Scenario: 缺少输入被拒绝
- **WHEN** 生成或保存时岗位名称与需求描述均缺失
- **THEN** 返回校验错误（422）

### Requirement: JD SSE 流式生成

系统 SHALL 以 SSE 流式返回 JD 生成过程，事件序列为 `thinking` → `delta`（多次）→ `final`，`final` 携带完整结构化 JD。

#### Scenario: 事件序列正确
- **WHEN** 调用流式生成接口
- **THEN** 依次收到 `thinking`、若干 `delta`、`final` 事件

#### Scenario: 流式中断可重试
- **WHEN** 客户端中断流式连接
- **THEN** 服务端停止生成；重新调用可再次生成（不静默丢输入）

### Requirement: JD CRUD 与状态机

系统 SHALL 支持 JD 列表/详情/创建/更新/删除，状态取 `draft` / `published` / `archived`，默认 `draft`。

#### Scenario: 状态流转守卫
- **WHEN** 更新 JD 状态为非法值
- **THEN** 拒绝（422）

#### Scenario: 删除需授权
- **WHEN** 无 HR 管理权限的用户删除 JD
- **THEN** 返回 403
