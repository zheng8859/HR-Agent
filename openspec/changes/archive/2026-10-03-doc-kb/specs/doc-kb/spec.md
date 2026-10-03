# doc-kb Specification

## Purpose
定义文档处理与知识库后端能力：文档上传与 SHA256 哈希、文本提取、语义切片、向量化入 pgvector、文档状态机、知识库 CRUD、删除级联、用户隔离。

## ADDED Requirements

### Requirement: 文档上传与哈希

系统 SHALL 支持上传 PDF/DOC/DOCX/TXT 文档，保存原始文件到 uploads，记录 SHA256 哈希、大小与 MIME。

#### Scenario: 上传校验
- **WHEN** 上传非法格式或超限文件
- **THEN** 返回 422，不落库

#### Scenario: 上传落盘并记录哈希
- **WHEN** 上传合法文档
- **THEN** 原始文件保存到 uploads，记录 SHA256 哈希、大小、MIME

### Requirement: 文本提取

系统 SHALL 支持从 PDF/DOC/DOCX/TXT 提取纯文本；提取为空时标记失败并给出明确提示。

#### Scenario: 提取为空标记失败
- **WHEN** 提取不到文本内容
- **THEN** 文档状态置为 failed 并提示解析失败，不当作可检索知识

### Requirement: 语义切片

系统 SHALL 将文档文本语义切片，每段 ≤500 字、严禁 >800 字；超长强制切分、过短合并。

#### Scenario: 超长强制切分
- **WHEN** 某段超过 800 字
- **THEN** 强制切分为不超过 500 字的分段

#### Scenario: 过短合并
- **WHEN** 尾部片段过短
- **THEN** 合并至上一段，避免碎片化

### Requirement: 向量化

系统 SHALL 使用 Embedding 生成 1536 维向量并写入 pgvector。

#### Scenario: 维度为 1536
- **WHEN** 向量化文档内容
- **THEN** 生成 1536 维向量并写入 embedding 列

### Requirement: 文档状态机

系统 SHALL 维护文档状态机 `uploaded → processing → processed / failed`，失败可重新处理。

#### Scenario: 处理成功
- **WHEN** 文档处理成功
- **THEN** 状态为 processed

#### Scenario: 处理失败可重试
- **WHEN** 文档处理失败
- **THEN** 状态为 failed，且可触发重新处理

### Requirement: 知识库 CRUD

系统 SHALL 支持知识库增删改查，名称唯一；删除知识库前检查是否含文档。

#### Scenario: 名称唯一
- **WHEN** 创建重名知识库
- **THEN** 返回冲突错误

#### Scenario: 含文档拒绝删除
- **WHEN** 删除仍含文档的知识库
- **THEN** 返回 409，拒绝删除

### Requirement: 删除级联清理

系统 SHALL 在删除文档时同步清理其切片与向量，删除后不再被检索。

#### Scenario: 删除后不可检索
- **WHEN** 删除文档
- **THEN** 该文档及其向量被移除，不再出现在列表与检索范围

### Requirement: 用户隔离

系统 SHALL 保证用户只能访问自己上传的文档（按 `user_id` 过滤，collection 按用户划分）。

#### Scenario: 跨用户不可见
- **WHEN** 用户查询他人文档
- **THEN** 返回 404 或空列表
