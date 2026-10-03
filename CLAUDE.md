# CLAUDE.md — HR Agent 项目开发指引

> 本文件是 Claude Code 在本仓库工作的行为准则与工具链速查，从《00-总体开发方案.md》与第四部分产品设计文档（10~24）提炼。开工前请确认已读《00-总体开发方案.md》。

## 一、项目定位

HR Agent —— 企业人力资源 AI 助手。核心理念是「**受控自动化**」：AI 干重复活（出初稿），人做关键决定（定终稿），不越界。

本期四大模块：**智能招聘**（JD / 评分标准 / 简历评估 / 面试方案，四环节闭环）+ **知识助理**（文档处理 / RAG 问答）+ **Agent 对话入口** + **系统管理**（用户 / 角色）。

## 二、技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + Vue Router + Pinia + Element Plus + ECharts |
| 后端 | FastAPI + SQLAlchemy Async + Pydantic |
| 数据 | PostgreSQL + pgvector（向量检索，Embedding 1536 维） |
| 认证 | JWT + OAuth2 Password Bearer + bcrypt |
| AI | Dify 工作流（type=1~4）+ Qwen LLM + Embedding + Rerank（gte-rerank-v2） |
| 部署 | Docker / Docker Compose |

运行要求：Node.js ≥ 20.19.0；Python 3.11+。

## 三、工具链与工作流

```
思考层： /office-hours  /plan-ceo-review  /plan-eng-review    ← Gstack
规格层： /opsx:propose  →  /opsx:apply  →  /opsx:archive      ← OpenSpec
实现层： 写测试(RED)  →  Claude生成(GREEN)  →  重构           ← TDD
质量层： L1单元  →  L2集成  →  L3 Golden  →  基线对比        ← Evals
流程层： /review  /cso  /qa  /ship  /retro  /investigate      ← Gstack
骨架层： branch  commit  tag  merge  revert  push              ← Git
```

### 标准阶段流程

```
1. git checkout -b phase-N/xxx
2. /opsx:propose "实现XXX功能"
3. /opsx:apply              ← 内部 TDD 循环 + Evals 检查
4. /review                  ← 代码审查
5. /qa browse               ← 浏览器验收（如有 UI）
6. git checkout main && git merge --no-ff phase-N/xxx && git tag -a v0.N.0
7. /opsx:archive
```

### 何时用什么

| 场景 | 用哪个 | 不用哪个 |
|------|--------|---------|
| 设计文档已明确定义的功能 | `/opsx:propose` → `/opsx:apply` | 跳过思考层（已决策不反复讨论） |
| 架构级决策（Agent 编排、Dify 边界） | `/plan-eng-review` | — |
| 每个模型/组件完成 | `git commit`（原子化） | 不攒批提交 |
| Evals 通过 | `git tag evals-ok-YYYYMMDD` | — |
| Evals 劣化 > 5% | `/investigate` → 修复/回退 | — |
| 阶段完成 | `/review` → `merge --no-ff` → tag | — |
| 验收（前端页面/交互） | `/qa` `/qa-only` `/design-review` | — |
| 发布 / 复盘 | `/ship` / `/retro` | — |

## 四、Git 规范（Conventional Commits）

- 格式：`{type}({scope}): {subject}`
- type：`feat / fix / test / refactor / docs / chore / perf`
- scope：`model / auth / jd / scoring / resume / interview / doc / kb / rag / agent / intent / skill / stats / ui / eval / golden-NNN`
- **原子化提交**：每个模型/组件一个 commit，不攒批。

### 质量门禁（Git hooks）

```
pre-commit  →  pytest tests/ --tb=short -x   （L1 单元，<5 秒）
commit-msg  →  校验 Conventional Commits 格式
pre-push    →  run_evals --tier all --compare baseline.json  （劣化 >5% 阻断）
```

### 版本节奏

```
v0.1.0 环境搭建 · v0.2.0 数据模型+认证 · v0.3.0 招聘 · v0.4.0 知识+系统管理
v0.5.0 Evals · v0.6.0 Agent · v1.0.0-rc.1 验收 · v1.0.0 发布
```

## 五、三层质量体系

**TDD 管"系统正确性"，Evals 管"AI 输出质量"——两层都要过，不能互相替代。**

| 层级 | 测什么 | 测试集 | 通过标准 | 运行时机 |
|------|--------|--------|:------:|---------|
| Agent 编排层 | 意图/工具调用/契约/人工确认 | `agent_cases/` | ≥90% | 工具组完成、push 前 |
| 内容生成层 | JD/评分/面试方案质量（结构/分值配平） | `dify_cases/` | ≥75% | 每日收工、push 前 |
| 知识问答层 | RAG 检索指标 + 生成指标 | `rag_cases/` | ≥70% | 每日收工、push 前 |

- **测试集是活资产**：每次真实踩坑补进对应测试集，防再犯。
- 劣化决策树：≤3% 记录 devlog → 3-5% `/investigate` 定位修复 → >5% revert 或修复。

## 六、设计铁律（必须遵守）

1. **受控自动化**：AI 出初稿、人定终稿，不越界。所有 AI 产物先落"可编辑态"，人确认后才生效。
2. **权限真门在后端**：`get_current_user` / `get_current_superuser` / `get_current_admin_by_role` 依赖注入是**唯一安全边界**。前端隐藏只是体验优化，绝不能把"前端隐藏"当鉴权——后端接口必须再次校验。
3. **高风险动作锁定**：删除 → 二次确认；发送类 → 只出草稿（邮件本期不做）。
4. **可解释才可信**：评分带维度分 + 理由，问答带来源依据。
5. **边界先于能力**：工具只能调注册表内的，清单外一律不碰；无依据宁可拒答不编造。

## 七、本期范围（确认口径）

- **角色**：4 种代码枚举 `admin / hr_manager / hr_specialist / employee`；"培训管理员"本期不落地（动态 Role 表承接）。
- **做**：招聘四环节、知识助理、Agent 对话、系统管理（用户/角色）。
- **不做**：智能培训（试卷/考试，Dify type=5/6）、邮箱配置（EmailConfig 实体、邮件 Skill 留接口）、自注册（账号仅超管在用户管理创建）。

## 八、目录与数据约定

- 后端 `hragent-backend/app/`：`api/v1/endpoints`、`core`、`models`、`schemas`、`services`、`skills`、`evaluations`。
- 前端 `hragent-frontend/src/`：`views`、`components`、`router`、`store`、`api`、`assets`。
- **10 张本地表**：User / Role / Conversation / Message / JobDescription / ScoringCriteria / ResumeEvaluation / InterviewPlan / Document / KnowledgeBase（全部本地 PostgreSQL）。
- **招聘四环节外键闭环**：JD → 评分标准 → 简历评估 → 面试方案（`job_description_id` / `scoring_criteria_id` / `resume_evaluation_id` 外键关联）。

## 九、pgvector 用法（0.5.0 注意）

pgvector Python 包 0.4.0+ 改了导入路径，本项目锁定 0.5.0。旧写法 `from pgvector.asyncpg import Vector` 已失效，正确写法：

```python
from pgvector import Vector                   # Vector 类型（顶层导入，如 Vector(1536)）
from pgvector.asyncpg import register_vector  # 连接级编解码器注册

await register_vector(conn)                   # 签名: (conn, /, *, schema='public')
```
