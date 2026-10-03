# Proposal

## Why

HR Agent 的核心业务（招聘四环节、知识问答、Agent 对话、系统管理）都建立在「本地结构化数据 + 用户身份与权限」之上。当前后端只有文档 34 留下的骨架空桩——模型、认证、权限依赖注入均未实现。本变更是整个系统的地基：先把 10 个本地模型、JWT 认证与 4 角色 RBAC 权限矩阵建起来，后续招聘/知识/Agent 各阶段才能在其上叠加。

## What Changes

- 新增 10 个本地 SQLAlchemy 模型（统一继承 `BaseModel`：`id`(UUID)/`created_at`/`updated_at`/`is_active`/`created_by`/`updated_by`）：
  - 身份：`User`、`Role`（+ `user_role` 多对多中间表）
  - 对话：`Conversation`、`Message`（`parent_message_id` 自引用）
  - 知识：`KnowledgeBase`、`Document`（`embedding` = `Vector(1536)`）
  - 招聘四环节（本地表、外键闭环）：`JobDescription` → `ScoringCriteria` → `ResumeEvaluation` → `InterviewPlan`
- 新增状态枚举 `jd_status`（draft/published/archived）与 `scoring_status`（draft/active/archived）。
- 新增 JWT 认证：OAuth2 密码流签发 + `python-jose` 校验 + `passlib[bcrypt]` 密码哈希，含令牌过期与篡改防护。
- 新增 RBAC 权限矩阵：4 角色 `admin / hr_manager / hr_specialist / employee`，配断言测试。
- 新增 FastAPI 依赖注入：`get_current_user` / `get_current_superuser` / `get_current_admin_by_role`。
- 新增 Alembic 初始化迁移（async engine + vector 扩展）。

**本期不建**（明确排除在 scope 外）：`Exam`/`Question`/`ExamResult`（培训）、`EmailConfig`/`EmailFetchLog`（邮箱）。

## Capabilities

### New Capabilities

- `identity`: 用户与角色——账号字段、4 角色代码枚举、`user_role` 多对多关联、超级管理员/启用状态。
- `conversation`: 会话与消息——会话生命周期状态（active/archived/deleted）、消息角色、父子链自引用。
- `knowledge`: 知识库与文档——文档元数据、pgvector 向量列（`Vector(1536)`）、文档归属知识库。
- `recruitment`: 招聘四环节本地数据——JD/评分标准/简历评估/面试方案四实体，外键闭环（面试方案必须绑定一条已完成评估）。
- `authentication`: JWT 认证——OAuth2 密码流签发、令牌校验/过期/篡改防护、bcrypt 密码哈希。
- `authorization`: RBAC 授权——4 角色权限矩阵与 FastAPI 依赖注入（执行顺序：认证 → 权限 → 业务逻辑）。

### Modified Capabilities

<!-- 无既有 spec（openspec/specs/ 为空），本变更为全新能力，无需 delta 修改。 -->

## Impact

- 代码：`hragent-backend/app/models/*`、`app/core/{database,security,deps,config}.py`、`tests/conftest.py`、`alembic/`。
- 依赖：`requirements.txt` 已声明 `python-jose[cryptography]`、`passlib[bcrypt]`、`pgvector`、`asyncpg`、`alembic`，无需新增。
- 数据库：PostgreSQL + pgvector（`Document.embedding` 用 `Vector(1536)`，**测试库必须 PostgreSQL 而非 SQLite**）。
- 无 BREAKING 变更（全部为新增表与新增模块，不修改既有表）。
