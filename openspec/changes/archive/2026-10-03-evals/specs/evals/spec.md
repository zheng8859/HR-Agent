# evals Specification

## Purpose
定义 AI 输出质量的评测体系：三套 Golden 测试集、确定性评测工具函数、三层粒度金字塔（L1/L2/L3 通过标准）、三评测器、CLI 运行器、回归基线与 CI 门禁，使每次改动都能度量「AI 变好还是变差」。

## ADDED Requirements

### Requirement: 三套 Golden 测试集

系统 SHALL 提供 agent（50）/ dify（40）/ rag（30）共 120 个标注样本，并以 JSON 存储、`schema.json` 定义三种样本结构。

#### Scenario: 样本分布
- **WHEN** 加载三套测试集
- **THEN** agent_cases=50、dify_cases=40、rag_cases=30，总计 120

#### Scenario: 样本结构校验
- **WHEN** 用 schema.json 校验每套样本
- **THEN** 所有样本字段结构与类型合法，无校验错误

### Requirement: 确定性评测工具函数

系统 SHALL 提供纯函数工具，覆盖结构完整性、分值配平、关键词覆盖、语义相似度、检索指标、生成指标与聚合。

#### Scenario: 结构完整度
- **WHEN** 计算生成内容对必备章节的覆盖
- **THEN** 返回覆盖率 ∈ [0,1]，漏「技能要求」等章节即降低

#### Scenario: 分值配平
- **WHEN** 校验评分标准维度分值之和
- **THEN** 维度分之和严格等于总分（如 100），否则标记未配平

#### Scenario: 关键词覆盖
- **WHEN** 计算生成内容覆盖要点关键词比例
- **THEN** 返回覆盖占比 ∈ [0,1]

#### Scenario: 检索与生成指标
- **WHEN** 计算检索 recall/hit/rank 与生成 faithfulness/relevance/citation
- **THEN** 返回各指标 ∈ [0,1]

#### Scenario: 聚合
- **WHEN** 聚合多样本评测结果
- **THEN** 返回通过率、分套/分类通过率与均值

### Requirement: 三评测器

系统 SHALL 提供 agent_eval / dify_eval / rag_eval 三评测器，分别对应三层错误类型；L3 无 LLM key 时以 mock 结果跑通框架。

#### Scenario: agent 评测
- **WHEN** 评测 Agent 编排样本
- **THEN** 检查意图/路由/契约字段精确匹配、确认判定、工具边界，并做语义裁判

#### Scenario: dify 评测
- **WHEN** 评测内容生成样本
- **THEN** 检查结构完整性、分值配平、关键词覆盖

#### Scenario: rag 评测
- **WHEN** 评测知识问答样本
- **THEN** 检索指标与生成指标分开计算

### Requirement: 三层粒度金字塔

系统 SHALL 以 L1/L2/L3 三层粒度运行测试，通过标准分别为 95% / 90% / 85%。

#### Scenario: 分层阈值
- **WHEN** 运行各层测试
- **THEN** L1≥95%、L2≥90%、L3 整体≥85%（三套按样本量加权）

#### Scenario: L3 套级红线
- **WHEN** 统计 L3 三套通过率
- **THEN** agent≥90%、dify≥75%、rag≥70%

### Requirement: CLI 运行器

系统 SHALL 提供 `run_evals.py` 支持分层/分套运行、慢速开关、基线对比、保存基线、HTML 与 JSON 输出。

#### Scenario: 分层与分套
- **WHEN** 传入 `--tier` 或 `--suite`
- **THEN** 运行指定层或套的评测并输出通过率

#### Scenario: 基线对比
- **WHEN** 传入 `--compare baseline.json`
- **THEN** 输出与基线的劣化报告（按 3%/5%/10% 分档）

#### Scenario: 保存基线
- **WHEN** 传入 `--save-baseline`
- **THEN** 将当前结果写为新的 baseline.json

### Requirement: 回归基线

系统 SHALL 维护回归样本清单，并在每次评测后单独验证这些样本；基线上调需复核、下调禁止。

#### Scenario: 回归样本验证
- **WHEN** 评测结束
- **THEN** 单独输出 golden_agent_007/021、golden_dify_003/012/024、golden_rag_005 的通过情况

### Requirement: 边界条件独立监控

系统 SHALL 对意图误判、分值配平、RAG 无依据拒答、高风险确认、SSE 契约单独标定阈值并独立输出。

#### Scenario: 意图误判子类
- **WHEN** 统计 `category=ambiguous` 子类
- **THEN** 意图准确率 ≥85% 且单独输出

#### Scenario: 分值配平
- **WHEN** 检查评分标准样本
- **THEN** 分值配平由规则检查 100% 通过

#### Scenario: 无依据拒答
- **WHEN** 统计 `should_refuse=true` 样本
- **THEN** 拒答通过率 ≥90% 且独立统计

#### Scenario: 高风险确认
- **WHEN** 统计 `category=risky` 样本
- **THEN** `requires_confirmation=true` 通过率 100%

#### Scenario: SSE 契约
- **WHEN** 校验 SSE 事件序列
- **THEN** 事件结构（thinking/plan/delta/final）完整率 100%

### Requirement: CI 门禁

系统 SHALL 提供 GitHub Actions 工作流：L1 通过率 <95% 阻断合并；L2/L3 劣化 >5% 自动评论告警。

#### Scenario: L1 阻断
- **WHEN** L1 通过率低于 95%
- **THEN** CI 以非零退出码阻断合并

#### Scenario: 劣化告警
- **WHEN** L2/L3 相对基线劣化超过 5%
- **THEN** 在 PR 中自动评论告警

### Requirement: 数据存储与种子

系统 SHALL 提供 `golden_samples` / `eval_runs` 表与 `seed_evals.py` 种子脚本。

#### Scenario: 种子导入
- **WHEN** 运行 seed_evals.py
- **THEN** 将 JSON 样本导入 golden_samples，重复导入幂等
