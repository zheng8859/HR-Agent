# Spec Delta

## Purpose

定义知识库与文档的持久化能力：文档元数据、pgvector 向量列（1536 维）、文档归属知识库。

## ADDED Requirements

### Requirement: 知识库唯一名称

知识库 SHALL 具备唯一 `name`。

#### Scenario: 知识库名称重复被拒绝
- **WHEN** 以已存在的 `name` 创建第二个知识库
- **THEN** 数据库唯一约束拒绝写入

### Requirement: 文档归属知识库

文档 SHALL 通过 `knowledge_base_id` 外键归属于某个知识库。

#### Scenario: 文档绑定知识库
- **WHEN** 创建文档并指定其 `knowledge_base_id`
- **THEN** 文档与知识库建立归属关系

### Requirement: 文档向量列

文档 SHALL 具备 `embedding` 向量列，维度为 1536，用于 pgvector 向量检索。

#### Scenario: 写入并读取 1536 维向量
- **WHEN** 向文档的 `embedding` 列写入一个 1536 维向量
- **THEN** 向量可完整存储并从 PostgreSQL 读回

### Requirement: 文档哈希去重

文档 SHALL 记录文件 SHA256 哈希（`file_hash`），用于识别重复上传。

#### Scenario: 相同内容识别为重复
- **WHEN** 两个文档的 `file_hash` 相同
- **THEN** 系统可据此识别为重复文档
