# Tasks

## 1. 基础设施：配置、数据库与测试夹具

- [x] 1.1 实现 `app/core/config.py`：在现有 `Settings` 基础上新增 `access_token_expire_minutes`、`jwt_algorithm`（HS256），保留 `database_url`/`secret_key`/`rag_min_similarity_score`。验证：导入 `settings` 后三项新配置均可读取、类型正确。
- [x] 1.2 实现 `app/core/database.py`：`create_async_engine` + `async_sessionmaker` + `get_db` 依赖 + 连接级 `register_vector`。验证：`get_db` 可 yield 一个可用 session（导入无错、引擎可创建）。
- [x] 1.3 实现 `tests/conftest.py`：异步 PostgreSQL 测试引擎（复用 docker-compose 实例，另建 `hragent_test` 库）→ `CREATE EXTENSION IF NOT EXISTS vector` → `create_all` → yield 异步 session。验证：pytest 能建立连接并建表（`fixture 'db_session'` 不再缺失）。

## 2. 模型基类与状态枚举

- [x] 2.1 实现 `app/models/base.py`：`BaseModel` 含 `id`(UUID 主键)/`created_at`/`updated_at`/`is_active`/`created_by`/`updated_by`。验证：base 模型字段测试通过（创建实体自动填充 id 与时间戳、is_active 默认 True）。
- [x] 2.2 实现 `app/models/jd_status.py`（draft/published/archived）与 `app/models/scoring_status.py`（draft/active/archived）。验证：两枚举取值测试通过。

## 3. 模型（按依赖链分组，每组随实现落测试）

- [x] 3.1 实现 `app/models/user.py`、`app/models/role.py` 与 `user_role` 多对多中间表（User：username/email 唯一、role 4 枚举、is_superuser/is_verified/last_login；Role：name 唯一/description/is_builtin）。验证：identity spec 测试通过（唯一约束、角色枚举、M2M 关联）。
- [x] 3.2 实现 `app/models/conversation.py`、`app/models/message.py`（status active/archived/deleted；message 角色 + `parent_message_id` 自引用）。验证：conversation spec 测试通过（默认 active、角色记录、父子链）。
- [x] 3.3 实现 `app/models/knowledge_base.py`、`app/models/document.py`（KB name 唯一；Document 含 `embedding`=Vector(1536)、`file_hash` SHA256、`knowledge_base_id` 外键）。验证：knowledge spec 测试通过（向量列可写读、唯一名、归属、哈希）。
- [x] 3.4 实现 `app/models/job_description.py`（status 用 jd_status 枚举、conversation_id/user_id 外键）。验证：JD 状态默认 draft 测试通过。
- [x] 3.5 实现 `app/models/scoring_criteria.py`（`job_description_id` 外键、`total_score` 默认 100、`scoring_dimensions`）。验证：评分标准绑定 JD + 默认总分测试通过。
- [x] 3.6 实现 `app/models/resume_evaluation.py`（`job_description_id`/`scoring_criteria_id` 外键、`evaluation_metrics` JSON、status pending/rejected/interview）。验证：简历评估双外键 + 默认 pending 测试通过。
- [x] 3.7 实现 `app/models/interview_plan.py`（`resume_evaluation_id` 非空外键、user_id）。验证：面试方案绑定简历评估测试通过。

## 4. 认证与权限

- [x] 4.1 实现 `app/core/security.py`：bcrypt 哈希/校验 + JWT 签发/解码（含过期时间）。验证：authentication spec 测试通过（签发/编解码/过期/篡改四场景）。
- [x] 4.2 实现 `app/core/deps.py`：`get_current_user` / `get_current_superuser` / `get_current_admin_by_role`（执行顺序：认证 → 权限 → 业务逻辑）。验证：authorization spec 测试通过（白名单/有效 token/过期 token/权限拒绝四场景 + 4 角色×资源矩阵断言）。

## 5. Alembic 迁移

- [x] 5.1 实现 `alembic/env.py` 接 async engine + `target_metadata` 指向 10 模型聚合的 `Base.metadata`，autogenerate 生成初始化迁移后人工审查（删除不期望的 default/nullable 差异）。验证：`alembic upgrade head` 无错误，10 表建成且含 `vector` 扩展。

## 6. 集成校验

- [x] 6.1 招聘四环节外键闭环测试：JD → 评分标准 → 简历评估 → 面试方案 全链关联与约束（面试方案必须绑定一条已完成评估）。验证：闭环测试通过。
- [x] 6.2 全量单元测试回归。验证：`pytest tests/ -v` 全部绿色。
