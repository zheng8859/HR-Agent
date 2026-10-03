# Design

## Context

doc 35 已建好 `JobDescription` / `ScoringCriteria` 本地表与状态枚举、JWT/RBAC 依赖注入。本变更把「JD 生成」与「评分标准生成」两环服务与端点补齐。当前 Dify 未配置（无 `.env` 密钥），按 doc 36 约定测试走 mock。

## Goals / Non-Goals

**Goals:**
- JD 双入口生成（表单直生 / 一句话解析）+ SSE 流式（thinking→delta→final）+ CRUD + 状态机。
- 评分标准生成（维度 name/weight/max_score/description）+ 总分默认 100 + 权重不配平人工确认（不自动掩盖）+ 绑定 JD。
- 后端权限真门：写操作 `get_current_admin_by_role`。
- 补齐 `/auth/login`，使招聘端点端到端可鉴权。

**Non-Goals:**
- 不做简历评估/面试方案（doc 37/38）。
- 不做前端页面（Phase B）。
- 不接真实 Dify（未配置密钥；DifyClient 支持 mock，配置后即可切真）。

## Decisions

1. **Dify 未配置 → DifyClient 双模式**：`DifyClient` 读 `settings.dify_base_url` / `settings.dify_api_key`；两者任一为空即 `mock` 模式，返回确定性假 JD/评分标准，保证测试与本地联调可跑。配置后无需改服务层。备选：在服务层硬编码 mock——放弃，切真时改点多。

2. **SSE 事件序列固定**：JD 生成流式接口按 `thinking → delta* → final` 逐事件 yield，`final` 携带完整结构化 JD（含字段），中断（客户端断开）时服务端停止生成、下次可重试。备选：一次性返回——放弃，违反 doc 20 流式协议。

3. **需求解析与生成解耦**：`parse_requirement` 把一句话拆成结构化字段（mock 下用简单关键字/占位解析），`generate_jd` 接收结构化输入产出正文。前端/对话可复用解析接口（doc 13「页面内也内置了解析能力」）。

4. **权重不配平只提示不修正**：`validate_balance` 计算 `sum(dim.max_score)` 是否等于 `total_score`，不等返回 `is_balanced=False` + 差值，服务与 schema 透传该标志，绝不自动改权重（doc 15 明确「不自动修正掩盖问题」）。

5. **评分标准绑定 JD 校验存在性**：`ScoringCriteria.job_description_id` 可为空，非空时校验目标 JD 存在，否则 404。

6. **写操作鉴权用 `get_current_admin_by_role`**：JD/评分标准的生成/保存/编辑/删除均属 HR 管理（doc 14 矩阵：admin/hr_manager/hr_specialist ✅），读操作 `get_current_user`（登录即可）。备选：超管专用——放弃，与 doc 14 矩阵冲突。

7. **auth 端点补齐**：`/auth/login`（OAuth2 password → verify → 签发 JWT）+ `/auth/me`。属 doc 35「认证体系」遗留，招聘端点端到端所需，一并补齐。

## Risks / Trade-offs

- [Dify 未配置] → mock 模式输出与真实工作流结构可能不一致。缓解：DifyClient 定义清晰输入/输出契约，切真时仅替换实现；真实接入时用 `curl -N` 观察流。
- [SSE 流式中断] → 客户端断开后服务端仍在生成会浪费算力。缓解：生成器捕获取消，流式接口可重试。
- [权重口径不配平] → AI 生成维度分值可能算不平。缓解：`validate_balance` 显式标志，保存前人工确认，不自动修正。

## Migration Plan

1. 无数据迁移（复用 doc 35 表）。`alembic upgrade head` 无需新迁移。
2. 新增 `httpx` 依赖（`pip install httpx`）。
3. 回滚：删除本变更新增服务/端点即可，无数据影响。

## Open Questions

（无——Dify 未配置已按 mock 决策，维度/权重口径按 doc 15 已明确。）
