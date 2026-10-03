# jd-generator-ui Specification

## Purpose
定义 JD 生成页的前端交互能力：双入口输入、流式生成展示、初稿编辑确认、已保存列表与删除二次确认。

## Requirements

### Requirement: JD 双入口输入

页面 SHALL 支持两种输入入口：表单字段直接填写，或一句话描述经解析后自动填充表单字段。

#### Scenario: 一句话描述解析填充
- **WHEN** 用户仅填写一句话描述并触发解析
- **THEN** 系统调用解析接口并将解析出的标题等字段回填到表单

#### Scenario: 表单字段直填
- **WHEN** 用户直接填写岗位名称等表单字段
- **THEN** 无需解析即可发起生成

### Requirement: 生成中禁用重复提交

生成进行中 SHALL 禁用生成按钮，避免重复提交。

#### Scenario: 生成中按钮禁用
- **WHEN** 生成请求进行中
- **THEN** 生成按钮处于禁用状态并展示加载反馈

### Requirement: 流式展示生成过程

页面 SHALL 以打字机效果流式展示 JD 生成内容。

#### Scenario: 流式接收并展示
- **WHEN** 后端以 SSE 推送生成事件
- **THEN** 页面按事件顺序渐进展示生成文本

### Requirement: 初稿可编辑与确认保存

AI 生成的 JD 初稿 SHALL 先落可编辑状态，用户编辑并确认后才保存生效。

#### Scenario: 编辑初稿后保存
- **WHEN** 用户编辑初稿内容并点击确认保存
- **THEN** 系统以编辑后的内容保存 JD，并进入已保存列表

### Requirement: 已保存 JD 列表与状态标签

页面 SHALL 展示已保存 JD 列表，并以状态标签区分 draft / published / archived。

#### Scenario: 列表展示状态标签
- **WHEN** 已保存 JD 列表加载完成
- **THEN** 每条 JD 展示对应状态标签（草稿/启用/已归档）

### Requirement: 生成失败保留输入可重试

生成失败时 SHALL 保留用户已填输入并允许重试，不得静默丢弃输入。

#### Scenario: 失败保留输入
- **WHEN** 生成请求失败
- **THEN** 页面展示错误提示，保留原有输入，并提供重试入口

### Requirement: 删除二次确认

删除 JD SHALL 在删除前进行二次确认。

#### Scenario: 删除前二次确认
- **WHEN** 用户点击删除
- **THEN** 弹出二次确认对话框，确认后才执行删除
