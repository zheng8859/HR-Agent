# 安全审计报告（doc 45 Step 2 /cso 等价执行）

- 审计日期：2026-10-03
- 审计范围：`hragent-backend/app/**` + `hragent-frontend/src/**` + 依赖清单 + Git 跟踪状态
- 审计方式：`/cso`（Gstack）不可用，按文档 45 §Step 2 的 6 类检查项手动等价执行
- **整体安全评分：A**（无 Critical / 无 High；1 项 Medium 配置项、若干 Low，均不阻断发布）

## 漏洞清单（按严重度）

| # | 严重度 | 类型 | 位置 | 影响 | 修复建议 |
|---|:---:|------|------|------|---------|
| 1 | Medium | 密钥强度 | `app/core/config.py:12` `secret_key="change-me-in-production"` | 生产若未用环境变量覆盖，JWT 可被伪造 | 生产通过 `.env` 注入强随机密钥（`openssl rand -hex 32`）；代码默认值仅限本地/测试 |
| 2 | Low | 依赖未锁定 | `requirements.txt` 未 pin 版本 | 供应链漂移 / 潜在 CVE | 生成 `requirements.lock` 或 pin 主版本 |
| 3 | Low | 依赖审计缺口 | 环境无 `pip-audit` | Python 依赖 CVE 未自动扫描 | CI 引入 `pip-audit`；本次已人工核对（见下） |

## 六类检查项结果

### 1. 依赖漏洞扫描
- `npm audit --omit=dev`：**0 vulnerabilities**。
- Python 侧：`pip-audit` 本机不可用，人工核对 `requirements.txt`（fastapi / sqlalchemy / asyncpg / python-jose / bcrypt / langchain 等，均为当前稳定线），未发现已知高危组合。

### 2. 认证与授权审查
- JWT 签发/校验集中在 `app/core/security.py`（`python-jose` + HS256），`exp` 有效期 24h，合理。
- 权限真门在后端：`get_current_user` / `get_current_superuser` / `get_current_admin_by_role` 三个依赖注入均已定义并接线。
- 端点门控矩阵：`users` / `roles` 全部走 `get_current_superuser`；简历评估写操作走 `get_current_admin_by_role`；其余业务端点走 `get_current_user`。唯一免认证端点为 `/health` 与 `/auth/login`（预期）。
- Agent 工具角色门控：`TOOL_ROLES = (admin, hr_manager, hr_specialist)`，employee 触发招聘/删除工具降级 chat（后端强制，前端隐藏仅为体验）。

### 3. 注入风险检查
- SQL：全程 SQLAlchemy ORM（参数化），**未发现原始 SQL / 字符串拼接**。
- XSS：前端无 `v-html`，Vue 插值默认转义；后端响应为 JSON，无反射型注入面。
- 命令注入：未发现 `os.system` / `subprocess` 携带用户输入调用。

### 4. 密钥与配置审计
- `.env` 未被 Git 跟踪（`git ls-files` 仅 `hragent-backend/.env.example`）；`.gitignore` 已含 `.env` / `.env.local` / `.env.*.local`。
- 未发现硬编码 API Key / 密码（扫描 `api_key=`, `secret_key=`, `password=` 模式，排除哈希校验与 OAuth 表单依赖）。

### 5. 数据安全
- 密码使用 `bcrypt` 哈希存储（`get_password_hash`），无明文。
- 审计日志经 `audit_logger` 结构化输出，未发现 PII 明文落入日志的路径。

### 6. 依赖链安全
- 见 #2/#3：未锁定 + 审计工具缺口，均记 Low。

## 结论

- 无 Critical / High 漏洞 → 满足发布门槛。
- Medium #1（SECRET_KEY）为配置项，生产部署前用环境变量替换即闭环，**不阻断** `v1.0.0-rc.1`，但必须在文档 46 发布运维中作为上线前强制检查项。
- 整体评分 **A**。
