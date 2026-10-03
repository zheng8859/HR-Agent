# Design

## Context

文档 34 已铺好骨架：`app/models/*`、`app/core/{config,database,security,deps}.py`、`tests/conftest.py`、`alembic/` 均为空桩；`requirements.txt` 已声明全部依赖（`sqlalchemy[asyncio]`、`asyncpg`、`pgvector`、`python-jose[cryptography]`、`passlib[bcrypt]`、`alembic`）；PostgreSQL 容器已就绪且已装 `vector` 扩展。本变更把这些桩填实。动机见 proposal.md。

## Goals / Non-Goals

**Goals:**
- 建立 10 个本地模型 + 状态枚举，实现招聘四环节外键闭环。
- 打通 JWT 认证链（签发/校验/过期/篡改）与 bcrypt 密码哈希。
- 落地 4 角色 RBAC 与三依赖注入函数。
- 生成可执行的 Alembic 初始化迁移。

**Non-Goals:**
- 不实现任何业务服务逻辑（JD 生成、RAG 检索等）——留待文档 36~44。
- 不建培训考试表与邮箱配置表。
- 不实现前端。

## Decisions

1. **异步引擎 + asyncpg**：`app/core/database.py` 用 `create_async_engine` + `async_sessionmaker`；测试沿用同一套异步栈（pytest-asyncio）。引擎与迁移统一 `connect_args={"ssl": False}`——容器内 Postgres 未启用 SSL，禁用后避开 asyncpg 在 Windows Proactor 事件循环下的 SSL 协商重置（实测 `ConnectionResetError: WinError 64`）。备选：同步 psycopg2——放弃，与项目「SQLAlchemy Async」技术栈不符。

2. **pgvector 导入（SQLAlchemy 集成，非原生 asyncpg）**：`Document.embedding` 用 `from pgvector.sqlalchemy import Vector`（`Vector(1536)`，SQLAlchemy 列类型，自带 bind/result processor）。**不用** `register_vector`——那是原生 asyncpg 的连接级编解码器，会与 SQLAlchemy 列类型冲突（实测会令 `from_text` 收到 numpy 数组而报错）；顶层 `from pgvector import Vector` 是数据值类型、非列类型，也不用于模型。备选：旧式 `pgvector.asyncpg.Vector`——已失效（pgvector 0.4.0+ 改了导入路径，本仓库锁定 0.5.0）。

3. **测试库必须 PostgreSQL**：`Document.embedding` 是 `Vector(1536)`，SQLite 不支持该类型。conftest 连 docker-compose 的 postgres 实例另建 `hragent_test` 库（或复用开发库的独立 schema），`create_all` 前执行 `CREATE EXTENSION IF NOT EXISTS vector`。备选：SQLite 内存库——放弃（Vector 列无法建表）；备选：测试中桩替 embedding 列——只在无法连库时兜底，不作为主方案。

4. **JWT 配置集中到 `Settings`**：`app/core/config.py` 增加 `access_token_expire_minutes`、`algorithm`（HS256），`secret_key` 保留默认占位、生产必须替换。备选：散落在 security.py 硬编码——放弃，违反「生产化要点」。

5. **依赖注入执行顺序**：`get_current_user`（认证）→ `get_current_superuser` / `get_current_admin_by_role`（权限）→ 业务逻辑；`get_current_superuser`/`get_current_admin_by_role` 内部先调用 `get_current_user`。备选：权限函数独立解析 token——放弃，重复解析且易漏掉「用户是否启用」校验。

6. **Alembic 初始化迁移**：用 `env.py` 接 async engine，`target_metadata` 指向 10 模型聚合的 `Base.metadata`，首版迁移由 autogenerate 生成后人工审查（删除不期望的 default/nullable 差异）。autogenerate 不会自动为 `pgvector` 列补 import，生成后须手动补 `from pgvector.sqlalchemy import Vector`。备选：手写迁移——放弃，10 表手写易漏字段。

7. **测试事件循环统一为 session 级**：`engine` fixture 为 session 级、`db_session` 为 function 级，pytest-asyncio 默认给两者分配不同事件循环，导致 asyncpg 连接池跨 loop 复用损坏（实测 `got result for unknown protocol state 3` / `cannot rollback`）。在 `pytest.ini` 设 `asyncio_default_fixture_loop_scope = session` + `asyncio_default_test_loop_scope = session` 统一循环。

## Risks / Trade-offs

- [passlib 1.7.4 与 bcrypt 5.0.0 版本兼容] → **已解决**：实测 passlib 1.7.4 读取 bcrypt 5.0.0 时抛 `AttributeError: module 'bcrypt' has no attribute '__about__'`。改为 `bcrypt` 直接调用（`bcrypt.hashpw`/`checkpw`），`requirements.txt` 中 `passlib[bcrypt]` → `bcrypt`；bcrypt 对 >72 字节密码抛 `ValueError`，由 schema 层 `max_length` 约束。
- [测试建表失败（Vector 列）] → 若 conftest 误用 SQLite 会直接建表失败。缓解：锁定 conftest 用 PostgreSQL + `CREATE EXTENSION IF NOT EXISTS vector` + `create_all`（不用 register_vector，见 Decision #2）。
- [外键约束导致测试 fixture 顺序错] → 违反依赖链则 insert 失败。缓解：fixture 顺序严格按 User/Role → Conversation/KnowledgeBase → Message/Document，招聘链按 JD → SC/RE → IP。
- [招聘四环节外键链断裂] → 面试方案若未绑定评估，防空转失效。缓解：`InterviewPlan.resume_evaluation_id` 设非空外键 + 关联完整性测试。
- [autogenerate 检测到不期望变更] → 默认值与数据库不一致。缓解：生成后人工审查迁移脚本，删除多余操作。

## Migration Plan

1. 后端环境 `alembic upgrade head` 建 10 表（含 `CREATE EXTENSION vector` 已在初始化脚本执行）。
2. 测试库由 conftest 独立 `create_all`，不依赖 alembic 版本链。
3. 回滚：`alembic downgrade base` 后重新 `upgrade head`；数据未上线，无数据迁移风险。

## Open Questions

（无——所有会影响 spec / 方案 / 任务拆分的决策均已在上述 Decisions 中确定。）
