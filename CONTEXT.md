# CONTEXT.md — HR Agent 核心领域术语

> 从第四部分产品设计文档（10~24）提取的核心领域术语，按类别分组。每条给出中英文名与一句话定义，供 AI 助手与开发者对齐口径。

## 一、核心实体（Core Entities）

| 中文 | English | 定义 |
|------|---------|------|
| 用户 | User | 系统账号，含用户名/邮箱/姓名/部门/职位/角色等字段，密码 bcrypt 哈希存储 |
| 角色 | Role | 权限集合，`name`/`description`/`is_builtin`，通过 `user_role` 多对多关联用户 |
| 会话 | Conversation | 一次对话，含标题、状态（active/archived/deleted） |
| 消息 | Message | 会话内单条消息，角色（user/assistant/system），支持父子链（`parent_message_id`） |
| 岗位描述 | JobDescription (JD) | 招聘岗位的结构化描述，状态 draft/published/archived，本地表 |
| 评分标准 | ScoringCriteria | 简历筛选的"统一尺子"，含评分维度（name/weight/max_score/description），总分默认 100 |
| 简历评估 | ResumeEvaluation | 简历 AI 评分结果，含总分/维度分/理由，状态 pending/rejected/interview |
| 面试方案 | InterviewPlan | 基于已评分候选人生成的专属面试方案，必须绑定一条简历评估 |
| 文档 | Document | 知识库文档，含 `embedding`（Vector(1536)）、文本内容、SHA256 哈希 |
| 知识库 | KnowledgeBase | 文档集合，含 `is_public`/`is_searchable`，按用户分 collection |
| 公共基类 | BaseModel | 所有模型继承，含 `id`(UUID)/`created_at`/`updated_at`/`is_active`/`created_by`/`updated_by` |

## 二、招聘概念（Recruitment）

| 中文 | English | 定义 |
|------|---------|------|
| JD 生成 | JD Generation | 将一句话需求/表单转为结构化 JD 初稿（Dify type=1），人编辑确认后保存 |
| 评分标准生成 | Scoring Criteria Generation | 基于 JD 生成评分维度与权重（Dify type=2），权重口径需人工确认 |
| 简历评估 / 筛选 | Resume Evaluation / Screening | 上传简历（PDF/DOC/DOCX≤10MB）→ AI 评分（Dify type=3），评分必带理由 |
| 面试方案生成 | Interview Plan Generation | 基于已评分候选人生成专属方案（Dify type=4），含流程/问题/追问/风险点 |
| 招聘四环节闭环 | Recruitment Closed Loop | JD → 评分标准 → 简历评估 → 面试方案，上一环节产出成为下一环节输入 |
| 评分维度 | Scoring Dimension | 评分标准的最小单元，含 name/weight/max_score/description |
| 评估指标 | evaluation_metrics | 简历评估的 JSON 结果，含每维度的 score/max/reason |
| 状态流转 | State Transition | JD draft→published→archived；评分 draft→active→archived；简历 pending→rejected/interview |

## 三、知识 / RAG 概念（Knowledge & RAG）

| 中文 | English | 定义 |
|------|---------|------|
| 文档处理 | Document Processing | 上传 → 提取文本 → 语义切片 → 向量化入 pgvector 的完整链路 |
| 语义切片 | Semantic Chunking | LLM 生成语义分割点，每段 ≤500 字、严禁 >800 字，超长强制切分、过短合并 |
| 向量化 | Embedding | 文本转 1536 维向量，写入 pgvector |
| 向量检索 | pgvector | PostgreSQL 的向量扩展，按用户分 collection 存储文档向量 |
| 查询改写 | Query Rewriting | LLM 扩展查询词（rewritten_query + expanded_keywords，最多 6 个） |
| 多路径检索 | Hybrid Retrieval | 向量召回 + tsvector 全文检索，加权合并（0.7×向量 + 0.3×文本） |
| 重排 | Rerank | 用 gte-rerank-v2 重排检索结果，失败降级为原始排序 |
| 知识问答 | RAG Q&A | 先翻资料再回答，返回答案 + 来源片段（documentChunks），无依据拒答 |
| 来源依据 | Citation | 回答附带的文档名+位置引用，是"可解释才可信"的载体 |

> 注：pgvector Python 包 0.5.0 起，Vector 类型从顶层 `pgvector` 导入（`from pgvector import Vector`），连接级用 `from pgvector.asyncpg import register_vector` 注册编解码器。

## 四、Agent 概念（Agent）

| 中文 | English | 定义 |
|------|---------|------|
| 意图识别 | Intent Classification | 判断用户输入是否为任务、是哪类任务（两层判断） |
| 快慢双通道 | Fast/Slow Channel | 快通道（关键词+附件启发式，便宜稳定）优先；慢通道（受控 ReAct，聪明但贵）兜底 |
| 工具注册表 | Tool Registry | Agent 的能力边界清单，声明 intent/route/前置条件，清单外一律不碰 |
| 条件缺口分类 | Gap Classification | 缺"信息"→对话追问；缺"确认"→请求授权 |
| 高风险动作锁定 | High-Risk Lock | 不可逆动作（删除）+ 外部动作（发送）必须确认，自动化做到"临门一脚"前 |
| 产物 | Artifacts | Agent 返回的结构化产物（JD/评分/简历结果/面试方案等 18 种类型） |
| 流式事件 | SSE Events | thinking → plan → delta → artifact → final（任务型另有 progress） |
| 会话记忆 | Conversation Memory | 读最近 12 条消息（≤6000 字符），用于 ReAct 决策与指代解析 |
| 固定工作流 + 技能 | Workflow + Skill | 高频工序走 Dify 固定工作流；扩展能力注册 Skill（SKILL.md + skill.json + 脚本） |

## 五、权限概念（Permission）

| 中文 | English | 定义 |
|------|---------|------|
| 基于角色的访问控制 | RBAC | 通过角色控制功能权限，4 角色代码枚举 admin/hr_manager/hr_specialist/employee |
| 超级管理员 | admin | 唯一全权限角色，仅它能碰系统管理（用户/角色） |
| HR 负责人 | hr_manager | 看得见不动手：可看统计/招聘结果，禁管理操作 |
| HR 专员 | hr_specialist | 招聘四环节的主场，培训/知识库/系统管理全禁 |
| 普通员工 | employee | 最轻权限，仅知识问答 |
| 权限真门在后端 | Backend-Enforced AuthZ | 前端隐藏是体验优化，后端依赖注入才是安全边界 |
| 依赖注入 | Dependency Injection | `get_current_user` / `get_current_superuser` / `get_current_admin_by_role` |
| 数据敏感分级 | Data Sensitivity | 账号/简历/面试方案为高敏感，对话记录为中，按级控访问与保留 |

## 六、评测概念（Evaluation）

| 中文 | English | 定义 |
|------|---------|------|
| 三层评估 | Three-Tier Evaluation | Agent 编排层 / 内容生成层 / 知识问答层，错误性质不同故分开测 |
| 测试集 | Test Cases | 三套固定用例集 agent_cases / dify_cases / rag_cases，是"活资产" |
| 规则检查 | Rule Check | 死板可靠的检查：输出空不空、字段全不全、分值配不平、有无禁用词 |
| LLM 裁判 | LLM-as-Judge | 让大模型当评委评语义质量（相关性/忠实度/理由充分性） |
| 重复运行 | Repeated Runs | 同用例跑多次，区分"随机波动"与"稳定但错误" |
| 回归对比 | Regression Compare | 修改后跑同批用例对比质量，劣化 >5% 阻断 |
| 基线 | baseline.json | 历史评测快照，`run_evals --compare baseline.json` 做回归对比 |

## 七、外部服务（External Services）

| 中文 | English | 定义 |
|------|---------|------|
| Dify | Dify | 固定工作流平台，承载 JD/评分/简历/面试生成（type=1~4） |
| 通义千问 | Qwen LLM | 文本生成、意图判断、知识问答的大模型 |
| 向量化服务 | Embedding Service | 文档切片转 1536 维向量 |
| 重排服务 | Rerank Service | gte-rerank-v2，检索结果重排，可降级 |

## 八、数据模型与认证架构（v0.2.0 · 阶段 35）

> 本节是 35-数据模型与认证体系 的架构口径，与 17/14/20 三份设计文档对齐。术语定义见一~七节，此处只补实体关系、依赖链与认证流程三件事。

### 8.1 实体关系概要（本地 10 模型）

```
User | Role（+user_role 中间表）
  └→ Conversation → Message（parent_message_id 自引用）
KnowledgeBase → Document（embedding = Vector(1536)）

招聘四环节外键闭环（全本地表）：
JobDescription ──job_description_id→ ScoringCriteria
JobDescription ──job_description_id→ ResumeEvaluation
ScoringCriteria ──scoring_criteria_id→ ResumeEvaluation
ResumeEvaluation ──resume_evaluation_id→ InterviewPlan
```

- 招聘三实体（JD / 评分标准 / 面试方案）**本地建表存 PostgreSQL**，不依赖任何远程服务。
- 面试方案必须绑定一条「已完成」的简历评估（`resume_evaluation_id` 外键，防空转）。

### 8.2 依赖链与外键创建顺序

```
① User、Role（+user_role 中间表）      ← 无外键依赖，最先建
② Conversation、KnowledgeBase           ← 引用 User
③ Message（→ Conversation）、Document（→ KnowledgeBase + User）
④ JobDescription（→ User / Conversation）
⑤ ScoringCriteria（→ JobDescription）、ResumeEvaluation（→ JobDescription + ScoringCriteria）
⑥ InterviewPlan（→ ResumeEvaluation）
```

### 8.3 认证流程

```
登录（OAuth2 密码流）
  → 校验用户名/密码（passlib[bcrypt] 哈希比对）
  → 签发 JWT（python-jose，含过期时间）
  → 后续请求带 Authorization: Bearer <token>
  → 依赖注入校验（执行顺序：认证 → 权限 → 业务逻辑）
      get_current_user            JWT 解析 + 用户存在 + 是否启用
      get_current_superuser       必须超级管理员
      get_current_admin_by_role   按角色判断管理员权限
  → 权限真门在后端：前端隐藏只是体验优化，后端依赖注入才是唯一安全边界
```
