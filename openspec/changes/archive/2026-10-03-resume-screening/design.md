# Design

## 目标

在现有 Vue 3 + Element Plus 前端中新增简历筛选页，对接已就绪的 `/resume-evaluation` 后端端点，实现「上传 → 选 JD/评分标准 → 评估 → 评分卡展示 → 状态流转 → 导出」闭环。

## 架构与文件

```
hragent-frontend/src/
  api/resumeEvaluation.js          # 端点客户端（upload/evaluate/list/status/export）
  utils/resume.js                  # 纯逻辑：前端文件校验、维度进度百分比
  views/ResumeScreeningView.vue    # 页面组件（上传区 + 候选人表 + 评分卡）
  router/index.js                  # 新增 resume-screening 路由
  layouts/MainLayout.vue           # 启用「简历筛选」菜单项
hragent-frontend/tests/
  resume.test.js                   # utils/resume.js 单测
```

## 端点映射

| 前端动作 | 端点 |
|---------|------|
| 上传简历 | `POST /resume-evaluation/upload`（multipart `file`）→ `{original_filename, file_type, resume_content}` |
| 智能评估 | `POST /resume-evaluation/evaluate`（`resume_content` + `job_description_id` + 可选 `scoring_criteria_id`/`original_filename`/`file_type`） |
| 列表 | `GET /resume-evaluation` |
| 状态流转 | `PATCH /resume-evaluation/{id}/status?status=` |
| 导出 | `GET /resume-evaluation/{id}/export` → `{candidate_name, candidate_position, total_score, dimensions[], status, text}` |

## 关键决策

1. **JD 必选**：评估必须绑定 JD（对齐后端 `evaluate` 与 doc 37「评估必须选 JD」），未选 JD 时禁用「智能评估」按钮。评分标准可选。
2. **评分以接口返回为准**：总分直接用后端 `total_score`，维度渲染后端 `evaluation_metrics`（`[{name, score, max, reason}]`），不前端臆算（doc 37 B3）。
3. **前端校验与后端一致**：`utils/resume.js` 的 `validateResumeFile` 复刻后端 `validate_upload` 的规则（扩展名 `pdf/doc/docx`、默认 ≤10MB），仅做体验优化，真正校验仍在后端（CLAUDE.md 六.2）。
4. **重复提交防护**：`evaluating` 标志 + 按钮 loading，评估期间禁用。
5. **导出**：后端返回结构化 JSON，前端组装可读文本报告并用 Blob 触发下载（`候选报告-{姓名}.txt`）。
6. **状态**：`pending`→待人工复核（info）、`interview`→进入面试（success）、`rejected`→淘汰（danger），用 `el-select` 由 HR 更新。
7. **空态**：无评估记录时 `el-empty` 引导先上传并评估。

## 测试策略

前端纯逻辑（`utils/resume.js`）用 `node --test` 单测（与现有 `balance.test.js`/`token.test.js` 同风格）；页面交互通过 `vite build` + 前后端联调（mock 模式）验证。无浏览器工具，故以构建 + 单元测试 + 接口集成验证替代 `/qa`。
