# Design

## 目标

新增智能面试前端页，对接 `interview-plan` 后端能力，还原原型 `smart-interview.html` 的核心交互：选候选人 → 生成 → 七要素展示 → 编辑保存 → 导出 / 重新生成，并覆盖空态。

## 页面结构

| 区块 | 内容 |
|------|------|
| 候选人选择栏 | `el-select` 列已完成评估候选人（姓名 · 岗位 · 综合评分），生成按钮 |
| 方案卡片 | AI 生成徽标 + 候选人快照（姓名/岗位/评分）+ 七要素分区 |
| 操作栏 | 在线编辑（切换编辑态）、保存、重新生成、导出 md / txt |

## 关键决策

1. **候选过滤**：仅 `total_score != null`（已完成评估）进入候选列表；`el-select` 为空时禁用并展示「先完成简历评估」空态引导，附「去简历筛选页」跳转。
2. **方案分区展示**：后端 `content` 为 markdown（`## 面试目标` 等七分区），前端用纯函数 `parsePlanSections(content)` 解析为 `[{title, body}]`，按分区渲染卡片；「核心问题」分区保留编号列表。
3. **编辑保存**：编辑态用 `el-input type="textarea"` 编辑原始 markdown，保存调 `PUT /interview-plans/{id}`；「受控自动化」——AI 出初稿、人定终稿。
4. **导出**：`GET /interview-plans/{id}/export?format=md|txt` 返回 `responseType: 'blob'`，前端以 `URL.createObjectURL` 触发下载，文件名 `面试方案-{姓名}.{md|txt}`（后端已带 UTF-8 BOM，Windows 记事本不乱码）。
5. **重新生成**：调 `POST /interview-plans/{id}/regenerate`，成功后内容更新；状态联动由后端保证（置 interview）。
6. **空态与失败态**：无已完成候选人 → 引导；无方案 → 生成引导；失败 → `ElMessage.error` 展示后端 detail。

## 测试策略

TDD：先写 `tests/interview.test.js` 覆盖 `parsePlanSections` 纯逻辑（七分区解析、核心问题编号、空内容、缺分区），全红后实现，迭代至全绿；页面交互以 `vite build` + `npm run test` + 前后端联调脚本验证。
